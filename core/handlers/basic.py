from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import sqlite_db


router = Router()


@router.message(Command(commands=['start', 'help']))
async def user_start_bot(message: Message, bot: Bot):
    """
    Запуск взаимодействия с ботом. Приветствие пользователей и добавление
    новых пользователей в БД по их id пользователя из тг
    """
    await delete_messages(message, bot, 0)

    if message.from_user.id == message.chat.id:
        await bot.send_message(
            message.from_user.id,
            f'Добро пожаловать в наш магазин, {message.from_user.first_name}.'
        )
        await sqlite_db.sql_add_user((message.from_user.id,
                                      message.from_user.first_name))
    else:
        await message.answer('Общение с ботом через ЛС, напишите ему:\n'
                             'https://t.me/NewDiplomaBot')


@router.callback_query(lambda x: x.data and x.data.startswith(('←shop ',
                                                               'shop→ ')))
async def arrow_button_shop(query: CallbackQuery, bot: Bot):
    """Переключение между товарами в магазине."""
    direction, new_index = query.data.split()
    await show_shop_command(query.message, bot, index=int(new_index))


@router.message(Command('shop'))
async def show_shop_command(message: Message, bot: Bot, index=1):
    """Вывод в чат товаров."""
    await delete_messages(message, bot, 0)
    read = await sqlite_db.sql_select_products()
    page = len(read)
    product = read[index-1]
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=product[1],
        caption=
        f'Название: {product[2]}\nОписание: {product[3]}\nЦена: {product[-1]}',
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text='← ',
                        callback_data=
                        f'←shop {index - 1 if index != 1 else page}'
                    ),
                    InlineKeyboardButton(
                        text=f'{index}/{page}',
                        callback_data=f' '
                    ),
                    InlineKeyboardButton(
                        text=' →',
                        callback_data=
                        f'shop→ {index + 1 if index != page else 1}'
                    )
                ],
                [InlineKeyboardButton(
                    text=f'Добавить в корзину "{product[2]}"',
                    callback_data=
                    f'add_cart {message.chat.id}, {product[0]}, {product[2]}'
                )]
            ]
        )
    )


async def delete_messages(message: Message, bot: Bot, count=0):
    """Удаляет все предыдущие сообщения в чате"""
    while True:
        try:
            await bot.delete_message(message.chat.id,
                                     message.message_id - count)
            count += 1
        except Exception:
            break
