from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons_row1 = [
        KeyboardButton(text="Статистика 📊"),
        KeyboardButton(text="Питання ❓")
    ]
    keyboard.add(*buttons_row1)
    buttons_row2 = [
        KeyboardButton(text="Розсилка 📬"),
        KeyboardButton(text="Вигрузити базу даних 💽")
    ]
    keyboard.add(*buttons_row2)
    buttons_row3 = [
        KeyboardButton(text="🔙 Назад")
    ]
    keyboard.add(*buttons_row3)
    return keyboard


def get_preview_markup():
    markup = InlineKeyboardMarkup()
    preview_button = InlineKeyboardButton("📤 Надіслати", callback_data="send_broadcast")
    cancel_button = InlineKeyboardButton("❌ Відміна", callback_data="cancel_broadcast")
    markup.row(preview_button, cancel_button)
    markup.one_time_keyboard = True
    return markup
