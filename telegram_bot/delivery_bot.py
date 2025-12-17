import logging
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/orders/")
BOT_TOKEN = "8093240750:AAG5eoFP6fxjdxtjYwH0p5FTsD1Sw0IOmY4"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище временных данных пользователя
user_state = {}


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Я бот для оформления заказов\nВведите пожалуйста ваше имя")
    user_state[message.from_user.id] = {"step": 1}


@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text

    if user_id not in user_state:
        await message.answer("Нажмите команду /start, чтобы оформить новый заказ.")
        return

    state = user_state[user_id]

    # Шаг 1 — имя клиента
    if state["step"] == 1:
        state["customer"] = text
        state["step"] = 2
        await message.answer("Введите название товара, который вы хотите заказать:")
        return

    # Шаг 2 — товар
    if state["step"] == 2:
        state["product"] = text
        state["step"] = 3
        await message.answer("Введите количество:")
        return

    # Шаг 3 — количество
    if state["step"] == 3:
        if not text.isdigit():
            await message.answer("Количество должно быть в числовом виде:")
            return
        state["quantity"] = int(text)
        state["step"] = 4
        await message.answer("Введите цену товара:")
        return

    # Шаг 4 — цена
    if state["step"] == 4:
        try:
            state["price"] = float(text)
        except ValueError:
            await message.answer("Цена должна быть в числовом формате")
            return

        # Все данные есть → отправляем заказ в API
        order_json = {
            "customer": state["customer"],
            "product": state["product"],
            "quantity": state["quantity"],
            "price": state["price"],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=order_json) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    order_id = data.get("id", "???")
                    await message.answer(f"Спасибо, заказ создан! ID вашего заказа: {order_id}")
                else:
                    await message.answer("Ошибка при создании заказа")

        # очищаем состояние
        del user_state[user_id]
        return


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
