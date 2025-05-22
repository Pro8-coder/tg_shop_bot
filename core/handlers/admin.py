from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import sqlite_db
from config import config
from core.handlers.basic import delete_messages
from core.keyboards import keyboards


router = Router()


class FSMAdmin(StatesGroup):
    """Класс машины состояний."""
    photo = State()
    name = State()
    description = State()
    price = State()


@router.message(Command(commands='administrator'))
async def make_changes_command(message: Message, bot: Bot):
    """Получаем ID текущего модератора(проверка прав)."""
    await message.delete()
    chat_member = await message.chat.get_member(message.from_user.id)
    group_id = int(config.group_id.get_secret_value())

    if message.chat.id == group_id and (chat_member.status == 'administrator'
                                        or chat_member.status == 'creator'):
        message = await bot.send_message(
            message.from_user.id,
            'Предоставлены права администратора',
            reply_markup=keyboards.admin_keyboard
        )
        await delete_messages(message, bot, 1)
    else:
        await message.answer(
            'Только администраторы могут использовать эту команду.')


@router.message(F.text.lower() == 'добавить')
async def fsm_start(message: Message, bot: Bot, state: FSMContext):
    """Начало диалога загрузки нового товара(запуск машины состояний)."""
    await delete_messages(message, bot, 1)
    if message.from_user.id == message.chat.id:
        await state.set_state(FSMAdmin.photo)
        await message.reply('Загрузить фото')


@router.message(F.text.lower() == 'отмена')
async def cancel_handler(message: Message, bot: Bot, state: FSMContext):
    """Выход из машины состояний."""
    await delete_messages(message, bot, 1)
    if message.from_user.id == message.chat.id:
        current_state = await state.get_state()

        if current_state is None:
            return

        await state.clear()
        await message.reply('Добавление отменено.')


@router.message(FSMAdmin.photo)
async def load_photo(message: Message, bot: Bot, state: FSMContext):
    """Принимает фото товара из машины состояний"""
    await delete_messages(message, bot, 1)
    if message.from_user.id == message.chat.id:
        await state.update_data(photo=message.photo[0].file_id)
        await state.set_state(FSMAdmin.name)
        await message.reply('Теперь введи название')


@router.message(FSMAdmin.name)
async def load_name(message: Message, bot: Bot, state: FSMContext):
    """Принимает имя товара из машины состояний."""
    await delete_messages(message, bot, 1)
    if message.from_user.id == message.chat.id:
        await state.update_data(name=message.text)
        await state.set_state(FSMAdmin.description)
        await message.reply('Введи описание')


@router.message(FSMAdmin.description)
async def load_description(message: Message, bot: Bot, state: FSMContext):
    """Принимает описание товара из машины состояний."""
    await delete_messages(message, bot, 1)
    if message.from_user.id == message.chat.id:
        await state.update_data(description=message.text)
        await state.set_state(FSMAdmin.price)
        await message.reply('Теперь укажи цену')


@router.message(FSMAdmin.price)
async def load_price(message: Message, bot: Bot, state: FSMContext):
    """Принимает цену товара из машины состояний и всё сохраняем в SQL"""
    await delete_messages(message, bot, 1)
    if message.from_user.id == message.chat.id:
        await state.update_data(price=float(message.text))
        data = await state.get_data()
        await sqlite_db.sql_add_product(data)
        await message.reply('Успешно добавлено.')
        await state.clear()


@router.callback_query(lambda x: x.data and x.data.startswith((
        '←delete_item ', 'delete_item→ ')))
async def arrow_button_delete_item(query: CallbackQuery, bot: Bot):
    """Переключение между товарами в магазине при удалении."""
    direction, new_index = query.data.split()
    await show_delete_item_command(query.message, bot, index=int(new_index))


@router.callback_query(lambda x: x.data and x.data.startswith('del_product '))
async def del_product_callback_run(query: CallbackQuery, bot: Bot):
    """Удаление товара из БД."""
    item = query.data.replace('del_product ', '').split(', ')
    await sqlite_db.sql_delete_product(item[0])
    await query.answer(text=f'"{item[1]}" удалено.', show_alert=True)
    new_index = int(item[2]) - 1 if int(item[2]) != 1 else int(item[-1]) - 1
    await show_delete_item_command(query.message, bot, index=int(new_index))


@router.message(F.text.lower() == 'удалить')
async def show_delete_item_command(message: Message, bot: Bot, index=1):
    """Вывод в чат списка товаров для выбора удаления."""
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
                        f'←delete_item {index - 1 if index != 1 else page}'
                    ),
                    InlineKeyboardButton(
                        text=f'{index}/{page}',
                        callback_data=f' '
                    ),
                    InlineKeyboardButton(
                        text=' →',
                        callback_data=
                        f'delete_item→ {index + 1 if index != page else 1}'
                    )
                ],
                [InlineKeyboardButton(
                    text=f'Удалить продукт "{product[2]}"',
                    callback_data=f'del_product {read[index - 1][0]}, '
                                  f'{product[2]}, {index}, {page}'
                )]
            ]
        )
    )
