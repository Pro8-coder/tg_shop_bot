from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import sqlite_db
from core.handlers.basic import delete_messages


router = Router()


@router.callback_query(lambda x: x.data and x.data.startswith('add_cart '))
async def add_cart_callback_run(query: CallbackQuery, bot: Bot):
    """Добавление товара в корзину."""
    item = query.data.replace('add_cart ', '').split(', ')

    if query.from_user.id == query.message.chat.id:
        await sqlite_db.sql_add_cart(tuple(item[:-1]))
        await query.answer(text=f'"{item[-1]}" добавлено в корзину.')
    else:
        await bot.send_message(
            chat_id=int(item[0]),
            text='Взаимодействие с ботом через ЛС, напишите ему:\n'
                 'https://t.me/NewDiplomaBot')


@router.callback_query(lambda x: x.data and x.data.startswith(('←cart ',
                                                               'cart→ ')))
async def arrow_button_cart(query: CallbackQuery, bot: Bot):
    """Переключение между товарами в корзине."""
    direction, new_index = query.data.split()
    await show_cart_command(query.message, bot, index=int(new_index))


@router.callback_query(lambda x: x.data and x.data.startswith('del_cart '))
async def del_cart_callback_run(query: CallbackQuery, bot: Bot):
    """Удаление товара из корзины."""
    print(query.data)
    item = query.data.replace('del_cart ', '').split(', ')
    print(item)
    await sqlite_db.sql_delete_cart(item[0])
    await query.answer(
        text=f'"{item[1]}" удалено из вашей корзины.',
        show_alert=True
    )
    new_index = int(item[2]) - 1 if int(item[2]) != 1 else int(item[-1]) - 1
    await show_cart_command(query.message, bot, index=int(new_index))


@router.message(Command(commands='cart'))
async def show_cart_command(message: Message, bot: Bot, index=1):
    """Вывод в чат товаров из корзины и встроенной клавиатуры."""
    await delete_messages(message, bot, 0)
    read = await sqlite_db.sql_select_cart_user(message.chat.id)
    page = len(read)

    if not read:
        await bot.send_message(message.chat.id, 'Корзина пуста')
    else:
        product = await sqlite_db.sql_select_products_id(read[index-1][1])
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=product[1],
            caption=f'Название: {product[2]}\n'
                    f'Описание: {product[3]}\n'
                    f'Цена: {product[-1]}',
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text='← ',
                            callback_data=
                            f'←cart {index - 1 if index != 1 else page}'
                        ),
                        InlineKeyboardButton(
                            text=f'{index}/{page}',
                            callback_data=f' '
                        ),
                        InlineKeyboardButton(
                            text=' →',
                            callback_data=
                            f'cart→ {index + 1 if index != page else 1}'
                        )
                    ],
                    [InlineKeyboardButton(
                        text=f'Удалить из корзины "{product[2]}"',
                        callback_data=f'del_cart {read[index-1][0]}, '
                                      f'{product[2]}, {index}, {page}'
                    )]
                ]
            )
        )
