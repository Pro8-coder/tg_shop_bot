import logging
from types import TracebackType
from typing import Type

import aiosqlite


class Database:
    """
    Инициализация объекта базы данных.

    :ivar path: Путь к файлу базы данных SQLite
    """
    def __init__(self, path: str) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """
        Устанавливает соединение с базой данных и включает поддержку внешних
        ключей ("PRAGMA foreign_keys = ON;").
        """
        self.connection = await aiosqlite.connect(self.path)
        await self.connection.execute("PRAGMA foreign_keys = ON;")

    async def close(self) -> None:
        """
        Закрывает соединение с базой данных, если оно было установлено.
        """
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def __aenter__(self) -> 'Database':
        """Вход в контекстный менеджер - устанавливаем соединение"""
        await self.connect()
        return self

    async def __aexit__(
            self,
            exc_type: Type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None
    ) -> None:
        """Выход из контекстного менеджера - закрываем соединение"""
        await self.close()


db = Database('data/shop.db')


async def sql_start() -> None:
    """Подключение/создание БД и таблиц."""
    async with db:
        try:
            await db.connection.execute("BEGIN TRANSACTION")

            async with db.connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                existing_tables = {row[0] for row in await cursor.fetchall()}

                table_definitions = {
                    'products': """
                        CREATE TABLE products(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            img TEXT,
                            name TEXT UNIQUE NOT NULL,
                            description TEXT,
                            price INTEGER NOT NULL
                        )
                    """,
                    'users': """
                        CREATE TABLE users(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER UNIQUE NOT NULL,
                            name TEXT
                        )
                    """,
                    'cart': """
                        CREATE TABLE cart(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            product_id INTEGER NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES users(user_id),
                            FOREIGN KEY (product_id) REFERENCES products(id)
                                ON DELETE CASCADE
                        )
                    """,
                    'orders': """
                        CREATE TABLE orders(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            order_id INTEGER UNIQUE NOT NULL,
                            order_info TEXT NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                    """
                }

                for table_name, ddl in table_definitions.items():
                    if table_name not in existing_tables:
                        try:
                            await cursor.execute(ddl)
                            logging.info(f"Создана таблица: {table_name}")
                        except aiosqlite.Error as e:
                            logging.error(
                                f"Ошибка создания таблицы {table_name}: {e}",
                                exc_info=True
                            )
                            raise RuntimeError(
                                f"Ошибка создания таблицы {table_name}: {e}"
                            ) from e

            await db.connection.commit()
            logging.info("База данных успешно инициализирована")

        except Exception as e:
            await db.connection.rollback()
            logging.error(
                f"Откат создания БД из-за ошибки: {e}",
                exc_info=True
            )
            raise


async def sql_add_user(data: tuple[int, str]) -> None:
    """
    Принимает кортеж из id и имени. Проверяет наличие id в БД и в случае
    отсутствия добавление клиента(from_user.id) в таблицу "users"
    (список клиентов по id тг).
    """
    async with db:
        try:
            async with db.connection.execute(
                    """
                    INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)
                    """,
                    data
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Добавлен пользователь: {data[0]}")

        except Exception as e:
            logging.error(
                f"Ошибка добавления пользователя: {e}",
                exc_info=True
            )


async def sql_add_product(data: dict[str, str | int | None]) -> None:
    """
    Принимает словарь из идентификатора изображения, имени, описания и цены.
    Добавляет продукт в таблицу "products".
    """
    async with db:
        try:
            async with db.connection.execute(
                """
                INSERT OR IGNORE INTO products (img, name, description, price) 
                VALUES (?, ?, ?, ?)
                """,
                tuple(data.values())
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Продукт {data} успешно добавлен")

        except Exception as e:
            logging.error(f"Ошибка добавления товара: {e}", exc_info=True)


async def sql_select_products() -> list[tuple]:
    """
    Чтение всей таблицы "products". Возвращает все товары в магазине
    (список кортежей).
    """
    async with db:
        try:
            async with db.connection.execute(
                    "SELECT * FROM products"
            ) as cursor:
                return await cursor.fetchall()

        except Exception as e:
            logging.error(f"Ошибка чтения товаров: {e}", exc_info=True)
            return []


async def sql_delete_product(product_id: int) -> None:
    """
    Принимает значение id продукта. Выполняет удаление продукта из таблицы
    "products".
    """
    async with db:
        try:
            async with db.connection.execute(
                    "DELETE FROM products WHERE id = ?",
                    (product_id,)
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Продукт {product_id} успешно удалён")

        except Exception as e:
            logging.error(f"Ошибка удаления товара: {e}", exc_info=True)


async def sql_add_cart(data: tuple[int, int]) -> None:
    """
    Принимает кортеж из id пользователя (id берётся из тг) и id товара.
    Выполняет добавление товара в таблицу "cart".
    """
    async with db:
        try:
            async with db.connection.execute(
                """
                INSERT OR IGNORE INTO cart (user_id, product_id) VALUES (?, ?)
                """,
                data
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Товар {data} добавлен в корзину")

        except Exception as e:
            logging.error(
                f"Ошибка добавления товара в корзину: {e}",
                exc_info=True
            )


async def sql_select_cart_user(user_id: int) -> list[tuple[int, int]]:
    """
    Принимает id пользователя (id берётся из тг). Осуществляет выборку по
    user_id из таблицы "cart". Возвращает список кортежей.
    """
    async with db:
        try:
            async with db.connection.execute(
                    "SELECT id, product_id FROM cart WHERE user_id = ?",
                    (user_id,)
            ) as cursor:
                return await cursor.fetchall()

        except Exception as e:
            logging.error(
                f"Ошибка выборки товаров из корзины пользователя "
                f"{user_id}: {e}",
                exc_info=True
            )


async def sql_select_products_id(
        product_id: int
) -> tuple[int, str | None, str, str | None, int] | None:
    """
    Принимает id продукта в таблице "products". Осуществляет выборку по id
    из таблицы "products". Возвращает один конкретный товар, в форме кортежа
    или None если запись не найдена.
    """
    async with db:
        try:
            async with db.connection.execute(
                    "SELECT * FROM products WHERE id = ?",
                    (product_id,)
            ) as cursor:
                return await cursor.fetchone()

        except Exception as e:
            logging.error(
                f"Ошибка выборки товара {product_id} из магазина: {e}",
                exc_info=True
            )


async def sql_delete_cart(cart_id: int) -> None:
    """
    Принимает id (id из корзины) продукта в корзине. Удаление строки (продукта)
    из таблицы 'cart'. Удаляет позицию из корзины по id записи в корзине.
    """
    async with db:
        try:
            async with db.connection.execute(
                    "DELETE FROM cart WHERE id = ?",
                    (cart_id,)
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Товар удалён из корзины")

        except Exception as e:
            logging.error(
                f"Ошибка удаления товара из корзины: {e}",
                exc_info=True
            )


async def sql_delete_all_cart(user_id: int) -> None:
    """
    Принимает id пользователя (id из тг). Удаление всех строк (очистка
    корзины) из таблицы "cart".
    """
    async with db:
        try:
            async with db.connection.execute(
                    "DELETE FROM cart WHERE user_id = ?",
                    (user_id,)
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Корзина {user_id} успешно очищена")

        except Exception as e:
            logging.error(
                f"Ошибка очистки корзины {user_id}: {e}",
                exc_info=True
            )


async def sql_add_order(data: tuple[int, int, str]) -> None:
    """
    Принимает кортеж содержащий id клиента, id заказа и информацию по
    заказу. Добавление заказа в таблицу "orders".
    """
    async with db:
        try:
            async with db.connection.execute(
                """
                INSERT OR IGNORE INTO orders (user_id, order_id, order_info) 
                VALUES (?, ?, ?)
                """,
                data
            ) as cursor:
                if cursor.rowcount > 0:
                    await db.connection.commit()
                    logging.info(f"Заказ успешно добавлен")

        except Exception as e:
            logging.error(
                f"Ошибка добавления заказа: {e}",
                exc_info=True
            )
