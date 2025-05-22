from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

"""Клавиатура админа"""
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Добавить')],
        [KeyboardButton(text='Удалить')]
    ],
    resize_keyboard=True
)

"""Клавиатура оплаты"""
pay_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Оплатить заказ', pay=True)]]
)

# """Клавиатура основная"""
# client_keyboard = ReplyKeyboardMarkup(keyboard=[
#     [KeyboardButton(text='Привет, БотМэн!')],
#     [KeyboardButton(text='Магазин')],
#     [KeyboardButton(text='Корзина')],
#     [KeyboardButton(text='Оплатить')]
# ], resize_keyboard=True)
