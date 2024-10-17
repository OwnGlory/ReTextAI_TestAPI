import logging
import asyncio
import aiohttp
import pandas as pd
from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from config import bot_env
from db import init_db, register_user, is_user_registered, save_texts
import sentry_sdk
from tempfile import NamedTemporaryFile
import os

try:
    sentry_sdk.init(bot_env.sentry_dsn)  # Инициализация Sentry
    SENTRY_ENABLED = True
except ImportError:
    SENTRY_ENABLED = False

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=bot_env.bot_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
api_token = bot_env.api_token
api_post = bot_env.host_post
api_get = bot_env.host_get
admin_chat_id = bot_env.admin_chat_id


async def paraphrase_text(session, text):
    try:
        async with session.post(api_post, json={
            "method": "paraphrase",
            "api_token": api_token,
            "text": text,
        }) as response:
            response.raise_for_status()
            response_data = await response.json()
            task_id = response_data["data"]["taskId"]

        paraphrased_text = None
        while True:
            async with session.get(
                api_get, params={"taskId": task_id}
            ) as response:
                response.raise_for_status()
                response_data = await response.json()
                if response_data["data"]["ready"]:
                    paraphrased_text = response_data["data"]["result"]
                    break
                await asyncio.sleep(1)
        return paraphrased_text
    except aiohttp.ClientResponseError as e:
        logging.error(f"Ошибка API: {e.status} - {e.message}")
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return None
    except Exception as e:
        logging.error(f"Непредвиденная ошибка: {str(e)}")
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        return None


async def unique_texts(texts):
    async with aiohttp.ClientSession() as session:
        tasks = [paraphrase_text(session, text) for text in texts]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result]


async def handle_docs(message: types.Message):
    try:
        user_id = message.from_user.id

        if not await is_user_registered(user_id):
            await message.answer(
                "Вы не зарегистрированы."
                "Пожалуйста, используйте команду /start для регистрации."
            )
            return

        document_id = message.document.file_id
        file_info = await bot.get_file(document_id)
        file_path = file_info.file_path
        file = await bot.download_file(file_path)
        if message.document.mime_type in [
            'application/vnd.openxmlformats'
            '-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ]:
            df = pd.read_excel(file)
            if 'text_column' not in df.columns:
                await message.answer(
                    "Пожалуйста, убедитесь, что столбец с текстами"
                    " назван 'text_column'."
                )
                return

            texts = df['text_column'].tolist()
            unique_results = await unique_texts(texts)
            df['unique_texts'] = unique_results

            await save_texts(user_id, df)

            # Создание временного файла
            with NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                df.to_excel(tmp.name, index=False)
                tmp.seek(0)
                document = types.FSInputFile(
                    tmp.name,
                    filename='unique_texts.xlsx'
                )

                # Отправка файла пользователю
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=document
                )

                # Отправка файла в админский чат
                if admin_chat_id:
                    tmp.seek(0)
                    await bot.send_document(
                        chat_id=admin_chat_id,
                        document=document
                    )

            os.remove(tmp.name)
        else:
            await message.answer(
                "Этот формат файла не поддерживается."
                " Пожалуйста, загрузите Excel файл."
            )
    except Exception as e:
        logging.error(f"Ошибка обработки документа: {str(e)}")
        if SENTRY_ENABLED:
            sentry_sdk.capture_exception(e)
        await message.answer(
            "Произошла ошибка при обработке файла."
            "Пожалуйста, попробуйте снова."
        )


async def start_command(message: types.Message):
    await message.answer(
        "Привет! Добро пожаловать в ReTextAI."
    )
    user_id = message.from_user.id
    username = message.from_user.username
    await register_user(user_id, username)
    await message.answer(
        "Вы успешно зарегистрированы!"
        "Теперь вы можете загружать Excel файлы для уникализации текстов."
    )


async def main():
    await init_db()
    router.message.register(
        handle_docs, F.content_type == types.ContentType.DOCUMENT
    )
    router.message.register(start_command, Command(commands=["start"]))
    dp.include_router(router)
    await dp.start_polling(bot, skip_updates=True)
