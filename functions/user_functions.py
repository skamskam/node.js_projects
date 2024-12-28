from aiogram import types
from keyboards.user_keyboard import main_keyboard
from database.user_db import create_table, add_user
from aiogram import types

async def greet_user(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    user_first_name = message.from_user.first_name
    create_table()
    add_user(user_id, user_name)
    keyboard = main_keyboard()
    await message.answer(f"Привіт, {user_first_name}!  Виберіть опцію:", reply_markup=keyboard)

async def back_to_menu(message: types.Message):
    keyboard = main_keyboard()
    await message.answer("Виберіть опцію:", reply_markup=keyboard)