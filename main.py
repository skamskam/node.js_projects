import logging
import re
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import bot_token, group_chat_id, admins, doctors
from database.user_db import add_phone_number_to_user, add_name_to_user, add_birth_date_to_user, add_appointment_to_db, create_appointments_table, save_question, get_question_id, get_question, save_answer_to_db
from functions.user_functions import greet_user, back_to_menu
from keyboards.user_keyboard import main_keyboard, get_confirmation_markup, get_declaration_data_markup, get_back_markup
from keyboards.admin_keyboard import admin_keyboard, get_preview_markup
from database.admin_db import get_active_users_count, get_users_count, get_questions_count, get_all_user_ids, get_unanswered_questions
from functions.admin_functions import export_database_to_excel
from states import MyState, MyAnotherState, AnswerState, QuestionState, BroadcastState

logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
    
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await greet_user(message)

@dp.message_handler(lambda message: message.text == "📑 Декларація")
async def declaration(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Надати дані для декларації", callback_data='provide_declaration_data'))
    await message.answer("Тут ви можете пришвидшити або дистанційно оформити декларацію з нашим лікарем.", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data == 'provide_declaration_data')
async def provide_declaration_data(query: types.CallbackQuery):
    markup = get_declaration_data_markup()
    await bot.send_message(query.message.chat.id, "Натисніть кнопку, щоб надіслати свій номер телефону:", reply_markup=markup)
    await MyState.phone_number_received.set()

@dp.message_handler(content_types=['contact'], state=MyState.phone_number_received)
async def contact_received(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)

    back_markup = get_back_markup()

    await bot.send_message(message.chat.id, "Будь ласка, введіть ваш ПІБ:", reply_markup=back_markup)
    await MyState.waiting_for_name.set()

NAME_REGEX = re.compile(r'^[A-Za-zА-Яа-яЁёҐґЄєІіЇї\'\-\s]+$')
DOB_REGEX = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')

@dp.message_handler(state=MyState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await state.finish()
        await back_to_menu(message)
        return
    if not NAME_REGEX.match(message.text):
        await message.answer("❌ Неправильний формат ПІБ. Будь ласка, введіть ПІБ у правильному форматі.")
        return

    user_real_name = message.text
    await state.update_data(real_name=user_real_name)

    await bot.send_message(message.chat.id, "Будь ласка, введіть дату вашого народження у форматі ДД.ММ.РРРР:")
    await MyState.waiting_for_dob.set()

@dp.message_handler(state=MyState.waiting_for_dob)
async def process_dob(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await state.finish()
        await back_to_menu(message)
        return

    if not DOB_REGEX.match(message.text):
        await message.answer("❌ Неправильний формат дати народження. Будь ласка, введіть дату у форматі ДД.ММ.РРРР.")
        return

    date_birth = message.text
    await state.update_data(date_of_birth=date_birth)

    data = await state.get_data()
    phone_number = data.get('phone_number', 'Номер телефону не надано')
    confirmation_message = (
        f"<b>Ви ввели наступні дані:</b>\n\n"
        f"<b>Номер телефону:</b> {phone_number}\n"
        f"<b>ПІБ:</b> {data['real_name']}\n"
        f"<b>Дата народження:</b> {data['date_of_birth']}\n\n"
        "<i>Все вірно?</i>"
    )
    confirm_markup = get_confirmation_markup()

    await bot.send_message(message.chat.id, confirmation_message, reply_markup=confirm_markup, parse_mode=ParseMode.HTML)
    await MyState.confirm_data.set()


@dp.callback_query_handler(lambda query: query.data in ['confirm_yes', 'confirm_no'], state=MyState.confirm_data)
async def confirm_data(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == 'confirm_yes':
        data = await state.get_data()
        user_id = callback_query.from_user.id
        add_phone_number_to_user(user_id, data['phone_number'])
        add_name_to_user(user_id, data['real_name'])
        add_birth_date_to_user(user_id, data['date_of_birth'])

        declaration_message = (
            f"<b>📑 Нова заява на декларацію:</b>\n\n\n"
            f"<b>Номер телефону:</b> {data['phone_number']}\n"
            f"<b>ПІБ:</b> {data['real_name']}\n"
            f"<b>Дата народження:</b> {data['date_of_birth']}"
        )
        await bot.send_message(group_chat_id, declaration_message, parse_mode=ParseMode.HTML)

        await state.finish()
        await bot.send_message(user_id, "Ваші дані для декларації оброблені, найблищим часом з вами зв'яжуться для уточнення деталей", reply_markup=main_keyboard())
    else:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await state.finish()
        await back_to_menu(callback_query.message)

@dp.message_handler(lambda message: message.text == "👨‍⚕️ Запис")
async def schedule(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Записатися на прийом", callback_data='make_an_appointment'))
    await message.answer("Тут ви можете записатися на прийом до вашого лікаря.", reply_markup=keyboard)
    
@dp.callback_query_handler(lambda query: query.data == 'make_an_appointment')
async def provide_declaration_data(query: types.CallbackQuery):
    markup = get_declaration_data_markup()
    await bot.send_message(query.message.chat.id, "Натисніть кнопку, щоб надіслати свій номер телефону:", reply_markup=markup)
    await MyAnotherState.phone_number_received.set()

@dp.message_handler(content_types=['contact'], state=MyAnotherState.phone_number_received)
async def contact_received(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)

    back_markup = get_back_markup()

    await bot.send_message(message.chat.id, "Будь ласка, введіть ПІБ пацієнта:", reply_markup=back_markup)
    await MyAnotherState.waiting_for_patient_name.set()


@dp.message_handler(state=MyAnotherState.waiting_for_patient_name)
async def process_patient_name(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await state.finish()
        await back_to_menu(message)
        return

    if not NAME_REGEX.match(message.text):
        await message.answer("❌ Неправильний формат ПІБ. Будь ласка, введіть ПІБ у правильному форматі.")
        return

    patient_real_name = message.text
    await state.update_data(patient_real_name=patient_real_name)

    doctor_keyboard = InlineKeyboardMarkup()
    doctor_keyboard.add(InlineKeyboardButton("👨‍⚕️ Бородай Євген Федорович", callback_data='doctor_1'))
    doctor_keyboard.add(InlineKeyboardButton("👩‍⚕️ Бондаренко Владислава Ігорівна", callback_data='doctor_2'))
    doctor_keyboard.add(InlineKeyboardButton("👩‍⚕️ Андрієнко Сергій Вікторович", callback_data='doctor_3'))

    await bot.send_message(message.chat.id, "Будь ласка, виберіть лікаря:", reply_markup=doctor_keyboard)
    await MyAnotherState.waiting_for_doctor_name.set()

@dp.callback_query_handler(lambda query: query.data in ['doctor_1', 'doctor_2'], state=MyAnotherState.waiting_for_doctor_name)
async def process_doctor_selection(callback_query: types.CallbackQuery, state: FSMContext):
    
    if callback_query.data == 'doctor_1':
        doctor_real_name = "Бородай Євген Федорович"
    elif callback_query.data == 'doctor_2':
        doctor_real_name = "Бондаренко Владислава Ігорівна"
    else:
        doctor_real_name = "Андрієнко Сергій Вікторович"

    await state.update_data(doctor_real_name=doctor_real_name)

    await bot.send_message(callback_query.message.chat.id, "Будь ласка, введіть бажаний час та дату прийому:")
    await MyAnotherState.waiting_for_dob.set()

@dp.message_handler(state=MyAnotherState.waiting_for_dob)
async def process_dob(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await state.finish()
        await back_to_menu(message)
        return

    date_birth = message.text
    await state.update_data(date_of_birth=date_birth)

    data = await state.get_data()
    phone_number = data.get('phone_number', 'Номер телефону не надано')
    confirmation_message = (
        f"<b>Ви ввели наступні дані:</b>\n\n"
        f"<b>Номер телефону:</b> {phone_number}\n"
        f"<b>ПІБ пацієнта:</b> {data['patient_real_name']}\n"
        f"<b>ПІБ лікаря:</b> {data['doctor_real_name']}\n"
        f"<b>Дата прийому:</b> {data['date_of_birth']}\n\n"
        "<i>Все вірно?</i>"
    )
    confirm_markup = get_confirmation_markup()

    await bot.send_message(message.chat.id, confirmation_message, reply_markup=confirm_markup, parse_mode=ParseMode.HTML)
    await MyAnotherState.confirm_data.set()

@dp.callback_query_handler(lambda query: query.data in ['confirm_yes', 'confirm_no'], state=MyAnotherState.confirm_data)
async def confirm_data(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == 'confirm_yes':
        data = await state.get_data()
        user_id = callback_query.from_user.id

        create_appointments_table()
        add_appointment_to_db(user_id, data['phone_number'], data['patient_real_name'], data['doctor_real_name'], data['date_of_birth'])

        declaration_message = (
            f"<b>📑 Нова заява на прийом:</b>\n\n\n"
            f"<b>Номер телефону:</b> {data['phone_number']}\n"
            f"<b>ПІБ пацієнта:</b> {data['patient_real_name']}\n"
            f"<b>ПІБ лікаря:</b> {data['doctor_real_name']}\n"
            f"<b>Дата прийому:</b> {data['date_of_birth']}"
        )
        await bot.send_message(group_chat_id, declaration_message, parse_mode=ParseMode.HTML)

        await state.finish()
        await bot.send_message(user_id, "Ваша заява на прийом прийнята, найблищим часом з вами зв'яжуться для уточнення деталей", reply_markup=main_keyboard())
    else:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await state.finish()
        await back_to_menu(callback_query.message)

@dp.message_handler(lambda message: message.text == "❔ Поставити питання")
async def ask_question(message: types.Message):
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    if not await state.get_state():
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Залишити питання", callback_data='ask_question'))
        await message.answer("Тут ви можете залишити питання, яке вас цікавить, і наші лікарі нададуть відповідь найближчим часом.", reply_markup=keyboard)


@dp.callback_query_handler(lambda query: query.data == 'ask_question')
async def ask_question_callback(query: types.CallbackQuery):
    await bot.send_message(query.message.chat.id, "Задайте ваше питання")
    await QuestionState.WaitingForQuestion.set()

    
@dp.message_handler(lambda message: message.text and message.text != "❔ Поставити питання", state=QuestionState.WaitingForQuestion)
async def handle_question(message: types.Message, state: FSMContext):
    question_text = message.text
    user_id = message.from_user.id
    user_name = message.from_user.username

    save_question(user_id, user_name, question_text)
    question_id = get_question_id(user_id, question_text)

    for doctor_id in doctors:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Відповісти", callback_data=f'reply_{user_id}_{question_id}'))

        await bot.send_message(doctor_id, f"Користувач @{user_name} (ID: {user_id}) задав питання:\n{question_text}", reply_markup=keyboard)

        await bot.send_message(message.chat.id, "Ваше питання було надіслано адміністраторам.")
    await state.finish()

@dp.callback_query_handler(lambda query: query.data.startswith('reply_'))
async def reply_to_question(query: types.CallbackQuery):
    user_id, question_id = map(int, query.data.split('_')[1:])

    question = get_question(user_id, question_id)

    if question and question[6] == 0:
        user_name = question[2]
        question_text = question[3]

        await bot.answer_callback_query(query.id, "Введіть відповідь на питання:")
        await bot.send_message(query.message.chat.id, f"Введіть відповідь на питання від користувача {user_name}:\n{question_text}")

        current_state = dp.current_state(chat=query.message.chat.id, user=query.from_user.id)
        async with current_state.proxy() as data:
            data['question_id'] = question_id
            data['user_id'] = user_id
            data['user_name'] = user_name
            data['doctor_id'] = query.message.chat.id
        await AnswerState.WaitingForAnswer.set()
    else:
        await bot.answer_callback_query(query.id, "Це питання вже отримало відповідь.")

@dp.message_handler(state=AnswerState.WaitingForAnswer)
async def save_answer(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        question_id = data['question_id']
        user_id = data['user_id']
        doctor_id = data['doctor_id']

    answer_text = message.text
    save_answer_to_db(question_id, answer_text)
    await bot.send_message(user_id, f"Відповідь на ваше питання від нашого лікаря:\n{answer_text}")
    await bot.send_message(doctor_id, "Ваша відповідь була надіслана користувачеві.")
    await state.finish()

@dp.message_handler(lambda message: message.text == '🔙 Назад')
async def back_to_menu_handler(message: types.Message):
    await back_to_menu(message)


                                                                    ###ADMIN###
                                                                    
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id in admins:
        keyboard = admin_keyboard()
        await message.answer("Ви увійшли в панель адміністратора.", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == 'Статистика 📊')
async def statistics_handler(message: types.Message):
    if message.from_user.id in admins:
        total_users = get_users_count()
        active_users = get_active_users_count()
        total_sales = get_questions_count()

        response_message = (
            f"👥 Загальна кількість користувачів: {total_users}\n"
            f"📱 Кількість активних користувачів: {active_users}\n"
            f"🛍️ Загальна кількість питань: {total_sales}"
        )
        await message.answer(response_message)

@dp.message_handler(lambda message: message.text == 'Вигрузити базу даних 💽')
async def export_database_handler(message: types.Message):
    if message.from_user.id in admins:
        await message.answer("Вигружаємо базу даних...")
        await export_database_to_excel(message)

@dp.message_handler(text='Розсилка 📬', state=None)
async def send_broadcast_prompt(message: types.Message):
    if message.from_user.id in admins:
        await bot.send_message(message.chat.id, 'Текст розсилки підтримує розмітку *HTML*, тобто:\n'
                                          '<b>*Жирний*</b>\n'
                                          '<i>_Курсив_</i>\n'
                                          '<pre>`Моноширний`</pre>\n'
                                          '<a href="ссилка-на-сайт">[Обернути текст у посилання](https://www.telegrambotsfromroman.com/)</a>'.format(),
                                 parse_mode="markdown")
        await bot.send_message(message.chat.id, "Введіть текст повідомлення або натисніть /skip, щоб пропустити:")
        await BroadcastState.text.set()

@dp.message_handler(state=BroadcastState.text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    logging.info(f"Отримано текст: {message.text}")
    async with state.proxy() as data:
        data['text'] = message.text
    await bot.send_message(message.chat.id, "Надішліть фото для додавання до повідомлення або натисніть /skip, щоб пропустити:")
    await BroadcastState.photo.set()

@dp.message_handler(content_types=['photo'], state=BroadcastState.photo)
async def process_broadcast_photo(message: types.Message, state: FSMContext):
    logging.info(f"Отримано фото: {message.photo[0].file_id}")
    async with state.proxy() as data:
        data['photo'] = message.photo[0].file_id
    await send_preview(message.chat.id, data, state) 
    await BroadcastState.preview.set()
    
async def send_preview(chat_id, data, state: FSMContext):
    markup = get_preview_markup()
    text = "📣 *Попередній перегляд розсилки:*\n\n"
    text += data.get('text', '')

    if 'photo' in data and data['photo'] is not None:
        await bot.send_photo(chat_id, data['photo'], caption=text, parse_mode="Markdown", reply_markup=markup)
    else:
        await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

    async with state.proxy() as stored_data:
        stored_data.update(data)

@dp.callback_query_handler(text="send_broadcast", state=BroadcastState.preview)
async def send_broadcast_to_users_callback(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get('text', '')
    photo = data.get('photo')
    await send_broadcast_to_users(text, photo, call.message.chat.id)
    await call.answer()
    
@dp.message_handler(commands=['skip'], state=[BroadcastState.text, BroadcastState.photo])
async def skip_step(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'text' not in data:
            data['text'] = None
        if 'photo' not in data:
            data['photo'] = None
    await send_preview(message.chat.id, data, state)
    if 'text' in data and 'photo' in data:
        await BroadcastState.preview.set()
    elif 'text' in data:
        await BroadcastState.photo.set()
    else:
        await BroadcastState.text.set()

async def send_broadcast_to_users(text, photo, chat_id):
    logging.info(f"Відправка розсилки: text={text}, photo={photo}")
    try:
        user_ids = get_all_user_ids()
        for user_id in user_ids:
            if text.strip():
                try:
                    if photo:
                        logging.info(f"Відправлення фото користувачу {user_id}")
                        await bot.send_photo(user_id, photo, caption=text, parse_mode='HTML')
                    else:
                        logging.info(f"Відправлення повідомлення користувачу {user_id}: {text}")
                        await bot.send_message(user_id, text, parse_mode='HTML')
                except Exception as e:
                    logging.warning(f"Помилка відправлення повідомлення користувачу з ID {user_id}: {str(e)}")

        await bot.send_message(chat_id, f"Розсилка успішно виконана для {len(user_ids)} користувачів.")
    except Exception as e:
        await bot.send_message(chat_id, f"Виникла помилка: {str(e)}")
        
@dp.callback_query_handler(text="cancel_broadcast", state=BroadcastState.preview)
async def cancel_broadcast_callback(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text("Розсилка відмінена.")
    await call.answer()

@dp.message_handler(lambda message: message.text == 'Питання ❓')
async def questions_handler(message: types.Message):
    if message.from_user.id in admins:
        unanswered_questions = get_unanswered_questions()
        if not unanswered_questions:
            await message.answer("Немає нових питань.")
        else:
            for question in unanswered_questions:
                user_id, user_name, question_text, question_id = question
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("Відповісти", callback_data=f'reply_{user_id}_{question_id}'))
                await message.answer(f"Користувач @{user_name} (ID: {user_id}) задав питання:\n{question_text}", reply_markup=keyboard)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)