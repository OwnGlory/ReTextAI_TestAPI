import aiosqlite
import pandas as pd
from config import bot_env


async def init_db():
    async with aiosqlite.connect(bot_env.db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS texts (
                user_id INTEGER,
                text_column TEXT,
                unique_text_column TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        ''')
        await db.commit()


async def register_user(user_id, username):
    async with aiosqlite.connect(bot_env.db_path) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        ''', (user_id, username))
        await db.commit()


async def is_user_registered(user_id):
    async with aiosqlite.connect(bot_env.db_path) as db:
        async with db.execute('''
            SELECT 1 FROM users WHERE user_id = ?
        ''', (user_id,)) as cursor:
            return await cursor.fetchone() is not None


async def save_texts(user_id, df):
    async with aiosqlite.connect(bot_env.db_path) as db:
        await db.executemany('''
            INSERT INTO texts (user_id, text_column, unique_text_column)
            VALUES (?, ?, ?)
        ''', [(
            user_id, row['text_column'], row['unique_texts']
        ) for index, row in df.iterrows()])
        await db.commit()


async def get_texts(user_id):
    async with aiosqlite.connect(bot_env.db_path) as db:
        async with db.execute('''
            SELECT text_column, unique_text_column
            FROM texts
            WHERE user_id = ?
        ''', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return pd.DataFrame(rows, columns=['text_column', 'unique_texts'])
