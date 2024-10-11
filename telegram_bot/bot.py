import logging
import asyncio

import aiohttp
import pandas as pd

from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from config import bot_env

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


async def paraphrase_text(session, text):
    # Создание задачи на перефразирование текста
    async with session.post(api_post, json={
        "method": "paraphrase",
        "api_token": api_token,
        "text": text,
    }) as response:
        response_data = await response.json()
        task_id = response_data["data"]["taskId"]

    # Проверка статуса задачи и получение результата
    paraphrased_text = None
    while True:
        async with session.get(
            api_get, params={"taskId": task_id}
        ) as response:
            response_data = await response.json()
            if response_data["data"]["ready"]:
                paraphrased_text = response_data["data"]["result"]
                break
            await asyncio.sleep(1)  # Ждать перед повторением

    return paraphrased_text


async def unique_texts(texts):
    async with aiohttp.ClientSession() as session:
        tasks = [paraphrase_text(session, text) for text in texts]
        return await asyncio.gather(*tasks)


async def send_welcome(message: types.Message):
    await message.answer(
        "Привет! Загрузите Excel файл для уникализации текстов."
    )


async def handle_docs(message: types.Message):
    document_id = message.document.file_id
    file_info = await bot.get_file(document_id)
    file_path = file_info.file_path
    file = await bot.download_file(file_path)

    if (message.document.mime_type == (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') or
       message.document.mime_type == 'application/vnd.ms-excel'):
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

        output_file_path = 'unique_texts.xlsx'
        df.to_excel(output_file_path, index=False)

        document = types.FSInputFile(output_file_path)
        await bot.send_document(chat_id=message.chat.id, document=document)
    else:
        await message.answer(
            "Этот формат файла не поддерживается."
            " Пожалуйста, загрузите Excel файл."
        )


async def main():
    router.message.register(send_welcome, Command(commands=["start"]))
    router.message.register(
        handle_docs, F.content_type == types.ContentType.DOCUMENT
    )

    dp.include_router(router)

    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
