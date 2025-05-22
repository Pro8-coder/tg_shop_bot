import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums.parse_mode import ParseMode

import sqlite_db
from config import config
from core.handlers import basic, admin, cart, pay


logging.basicConfig(
    level=logging.INFO,
    force=True
)


async def main():
    """Запуск бота и регистрация хэндлеров/роутеров"""
    storage = MemoryStorage()
    bot = Bot(token=config.bot_token.get_secret_value(),
              parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage)

    dp.include_routers(
        basic.router,
        cart.router,
        pay.router,
        admin.router
    )

    try:
        await sqlite_db.sql_start()
        logging.info("✅ База данных успешно подключена")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logging.info("🛑 Работа бота остановлена по запросу")
    except RuntimeError:
        logging.critical("💥 Бот остановлен из-за критической ошибки БД")
    except Exception as ex:
        logging.error(f"💥 Критическая ошибка в работе бота: {ex}",
                      exc_info=True)
    finally:
        await bot.session.close()
        await storage.close()
        await sqlite_db.db.close()
        logging.info("📴 Сессия бота корректно завершена")


if __name__ == "__main__":
    logging.info("🟢 Запуск бота...")
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"💥 Аварийное завершение: {e}")
