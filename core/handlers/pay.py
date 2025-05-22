from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ShippingQuery,
    ShippingOption,
    LabeledPrice,
    PreCheckoutQuery,
)

from config import config
import sqlite_db
from core.handlers.basic import delete_messages
from core.keyboards import keyboards


router = Router()


@router.message(Command(commands='pay'))
async def buy_process(message: Message, bot: Bot):
    """Оплата товаров из корзины."""
    await delete_messages(message, bot, 0)
    rows = await sqlite_db.sql_select_cart_user(message.from_user.id)
    if not rows:
        return await bot.send_message(message.from_user.id, 'Корзина пуста')

    prices = []

    for row in rows:
        prod = await sqlite_db.sql_select_products_id(row[1])
        prices.append(LabeledPrice(label=f'{prod[2]}',
                                   amount=int(float(prod[-1]) * 100)))

    await bot.send_invoice(
        chat_id=message.chat.id,
        title='Товар',
        description='У нас лучшие товары',
        payload='Payment through a bot',
        provider_token=config.pay_token.get_secret_value(),
        currency='rub',
        prices=prices,
        need_name=True,
        need_phone_number=True,
        need_email=True,
        need_shipping_address=True,
        is_flexible=False,
        reply_markup=keyboards.pay_keyboard,
    )


@router.shipping_query(lambda q: True)
async def shipping_process(shipping_query: ShippingQuery, bot: Bot):
    """Территориальная фильтрация для доставки и выбор типа доставки."""
    if shipping_query.shipping_address.country_code != 'RU' or \
            shipping_query.shipping_address.city != 'Санкт-Петербург':
        return await bot.answer_shipping_query(
            shipping_query_id=shipping_query.id,
            ok=False,
            error_message='Доставка товаров только в Санкт-Петербурге'
        )

    await bot.answer_shipping_query(
        shipping_query_id=shipping_query.id,
        ok=True,
        shipping_options=[
            ShippingOption(
                id='shipping',
                title='Доставка',
                prices=[LabeledPrice(label='До двери', amount=10000)]
            ),
            ShippingOption(
                id='pickup',
                title='Самовывоз',
                prices=[LabeledPrice(label='Забрать самому', amount=0)]
            )
        ]
    )


@router.pre_checkout_query(lambda q: True)
async def checkout_process(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Ответ для авто-проверки. Сохраняем инф о заказе в БД."""
    order_info = {
        'first_name': pre_checkout_query.from_user.first_name,
        'last_name': pre_checkout_query.from_user.last_name,
        'username': pre_checkout_query.from_user.username,
        'currency': pre_checkout_query.currency,
        'total_amount': pre_checkout_query.total_amount,
        'invoice_payload': pre_checkout_query.invoice_payload,
        'shipping_option_id': pre_checkout_query.shipping_option_id,
        'name': pre_checkout_query.order_info.name,
        'phone_number': pre_checkout_query.order_info.phone_number,
        'email': pre_checkout_query.order_info.email,
        'country_code':
            pre_checkout_query.order_info.shipping_address.country_code,
        'state': pre_checkout_query.order_info.shipping_address.state,
        'city': pre_checkout_query.order_info.shipping_address.city,
        'street_line1':
            pre_checkout_query.order_info.shipping_address.street_line1,
        'street_line2':
            pre_checkout_query.order_info.shipping_address.street_line2,
        'post_code': pre_checkout_query.order_info.shipping_address.post_code
    }
    order = (pre_checkout_query.from_user.id, pre_checkout_query.id,
             f'{order_info}')
    await sqlite_db.sql_add_order(order)
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def successful_pay(message: Message, bot: Bot):
    """Сообщение об успешной оплате."""
    await delete_messages(message, bot, 0)
    await sqlite_db.sql_delete_all_cart(message.from_user.id)
    await bot.send_message(
        message.chat.id,
        f'Платеж на сумму {message.successful_payment.total_amount // 100} '
        f'{message.successful_payment.currency} совершен успешно!'
    )
