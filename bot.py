import json
import os
import subprocess
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
import signal
import sys

def signal_handler(sig, frame):
    print('Bot stopping...')
    # Ваш код для graceful shutdown
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Ваш основной код бота

# Конфигурация
BOT_TOKEN = "8545358194:AAE_jf4VmyhKSZTIZbget8LCR_AQf21TJq0"
MONITORED_FILE = "monitored_tokens.json"

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class TradingBot:
    def __init__(self):
        self.monitored_tokens = self.load_monitored_tokens()
        self.user_states = {}  # Для хранения состояний пользователей

    @staticmethod
    def load_monitored_tokens():
        if os.path.exists(MONITORED_FILE):
            with open(MONITORED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"tokens": []}

    def save_monitored_tokens(self):
        with open(MONITORED_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.monitored_tokens, f, indent=2, ensure_ascii=False)

    def add_monitored_token(self, token_data, chat_id):
        token_info = {
            "symbol": token_data["symbol"],
            "spot_symbol": token_data["spot_symbol"],
            "chat_id": chat_id,
            "added_time": datetime.now().isoformat()
        }

        for token in self.monitored_tokens["tokens"]:
            if token["symbol"] == token_data["symbol"] and token["chat_id"] == chat_id:
                return False

        self.monitored_tokens["tokens"].append(token_info)
        self.save_monitored_tokens()
        return True

    def remove_monitored_token(self, symbol, chat_id):
        initial_count = len(self.monitored_tokens["tokens"])
        self.monitored_tokens["tokens"] = [
            token for token in self.monitored_tokens["tokens"]
            if not (token["symbol"] == symbol and token["chat_id"] == chat_id)
        ]

        if len(self.monitored_tokens["tokens"]) < initial_count:
            self.save_monitored_tokens()
            return True
        return False

    async def run_scripts(self):
        try:
            scripts = ["futures.py", "spot.py", "finally.py"]
            for script in scripts:
                if os.path.exists(script):
                    process = await asyncio.create_subprocess_exec(
                        "python", script,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        print(f"Ошибка в {script}: {stderr.decode()}")
                else:
                    print(f"Файл {script} не найден")
            return True
        except Exception as e:
            print(f"Ошибка запуска скриптов: {e}")
            return False

    def get_recent_tokens(self, count=12):
        try:
            with open('price_comparison_results.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data['data'][:count]
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return []

    async def check_price_alerts(self):
        if not self.monitored_tokens["tokens"]:
            return

        await self.run_scripts()

        try:
            with open('price_comparison_results.json', 'r', encoding='utf-8') as f:
                current_data = json.load(f)

            current_tokens = {token['symbol']: token for token in current_data['data']}
            tokens_to_remove = []

            for monitored_token in self.monitored_tokens["tokens"]:
                symbol = monitored_token['symbol']
                chat_id = monitored_token['chat_id']

                if symbol in current_tokens:
                    current_diff = current_tokens[symbol]['price_difference_percent']
                    if current_diff <= 0.4:
                        message = (
                            f"⚠️ ВНИМАНИЕ: Разница цен для {symbol} упала до {current_diff:.2f}%\n"
                            f"Фандинг: {current_tokens[symbol]['funding_rate']}\n"
                            f"Фьючерс: {current_tokens[symbol]['future_price']}\n"
                            f"Спот: {current_tokens[symbol]['spot_price']}"
                        )
                        try:
                            await bot.send_message(chat_id, message)
                        except Exception as e:
                            print(f"Ошибка отправки: {e}")
                        tokens_to_remove.append(monitored_token)
                else:
                    message = f"❌ Токен {symbol} больше не имеет разницы цен > 0.4%"
                    try:
                        await bot.send_message(chat_id, message)
                    except Exception as e:
                        print(f"Ошибка отправки: {e}")
                    tokens_to_remove.append(monitored_token)

            for token in tokens_to_remove:
                self.monitored_tokens["tokens"].remove(token)

            if tokens_to_remove:
                self.save_monitored_tokens()

        except Exception as e:
            print(f"Ошибка при проверке цен: {e}")


trading_bot = TradingBot()


# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="My Position"), KeyboardButton(text="Show Token")],
            [KeyboardButton(text="Delete Token"), KeyboardButton(text="Back")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Back")]
        ],
        resize_keyboard=True
    )


def get_tokens_keyboard(tokens):
    keyboard = []
    for i, token in enumerate(tokens[:12]):
        keyboard.append([KeyboardButton(text=f"Open {token['symbol']}")])
    keyboard.append([KeyboardButton(text="Back")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_delete_keyboard(tokens):
    keyboard = []
    for token in tokens:
        keyboard.append([KeyboardButton(text=f"Delete {token['symbol']}")])
    keyboard.append([KeyboardButton(text="Back")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🤖 Trading Bot Activated\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "My Position")
async def show_my_position(message: Message):
    tokens = trading_bot.monitored_tokens["tokens"]
    user_tokens = [t for t in tokens if t['chat_id'] == message.chat.id]

    if not user_tokens:
        await message.answer(
            "📊 У вас нет активных отслеживаемых позиций",
            reply_markup=get_back_keyboard()
        )
        return

    message_text = "📊 Ваши отслеживаемые позиции:\n\n"
    for token in user_tokens:
        # Генерируем ссылки для каждого токена
        spot_url = f"https://www.mexc.com/ru-RU/exchange/{token['symbol']}"
        futures_url = f"https://www.mexc.com/futures/{token['symbol']}"

        message_text += f"• {token['symbol']}\n"
        message_text += f"  Добавлен: {token['added_time'][:16]}\n"
        message_text += f"  Ссылки: <a href='{spot_url}'>Спот</a> | <a href='{futures_url}'>Фьючерс</a>\n\n"

    await message.answer(
        message_text,
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


@dp.message(F.text == "Show Token")
async def show_tokens(message: Message):
    await trading_bot.run_scripts()

    tokens = trading_bot.get_recent_tokens(12)

    if not tokens:
        await message.answer(
            "❌ Нет данных о токенах с разницей > 0.4%",
            reply_markup=get_back_keyboard()
        )
        return

    # Сохраняем токены в состоянии пользователя для обработки кнопок "Open"
    trading_bot.user_states[message.chat.id] = tokens

    # Отправляем первый токен
    first_token = tokens[0]
    message_text = (
        f"🔹 {first_token['symbol']}\n"
        f"Разница: {first_token['price_difference_percent']}%\n"
        f"Фандинг: {first_token['funding_rate']}\n"
        f"Фьючерс: {first_token['future_price']}\n"
        f"Спот: {first_token['spot_price']}\n"
        f"Ссылки: <a href='{first_token['links']['spot_trading']}'>Спот</a> | "
        f"<a href='{first_token['links']['futures_trading']}'>Фьючерс</a>"
    )

    await message.answer(
        message_text,
        reply_markup=get_tokens_keyboard(tokens),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

    # Отправляем остальные токены
    for token in tokens[1:]:
        message_text = (
            f"🔹 {token['symbol']}\n"
            f"Разница: {token['price_difference_percent']}%\n"
            f"Фандинг: {token['funding_rate']}\n"
            f"Фьючерс: {token['future_price']}\n"
            f"Спот: {token['spot_price']}\n"
            f"Ссылки: <a href='{token['links']['spot_trading']}'>Спот</a> | "
            f"<a href='{token['links']['futures_trading']}'>Фьючерс</a>"
        )

        await message.answer(
            message_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )


@dp.message(F.text == "Delete Token")
async def delete_token_menu(message: Message):
    tokens = trading_bot.monitored_tokens["tokens"]
    user_tokens = [t for t in tokens if t['chat_id'] == message.chat.id]

    if not user_tokens:
        await message.answer(
            "❌ У вас нет отслеживаемых токенов для удаления",
            reply_markup=get_back_keyboard()
        )
        return

    message_text = "🗑️ Выберите токен для удаления:\n\n"
    for token in user_tokens:
        message_text += f"• {token['symbol']}\n"

    await message.answer(
        message_text,
        reply_markup=get_delete_keyboard(user_tokens)
    )


@dp.message(F.text.startswith("Delete "))
async def delete_token(message: Message):
    symbol = message.text.replace("Delete ", "")

    if trading_bot.remove_monitored_token(symbol, message.chat.id):
        await message.answer(
            f"✅ Токен {symbol} удален из отслеживания",
            reply_markup=get_back_keyboard()
        )

        # Показываем обновленный список токенов
        tokens = trading_bot.monitored_tokens["tokens"]
        user_tokens = [t for t in tokens if t['chat_id'] == message.chat.id]

        if user_tokens:
            message_text = "🗑️ Выберите токен для удаления:\n\n"
            for token in user_tokens:
                message_text += f"• {token['symbol']}\n"

            await message.answer(
                message_text,
                reply_markup=get_delete_keyboard(user_tokens)
            )
    else:
        await message.answer(
            f"❌ Токен {symbol} не найден в вашем списке отслеживания",
            reply_markup=get_back_keyboard()
        )


@dp.message(F.text.startswith("Open "))
async def open_token(message: Message):
    symbol = message.text.replace("Open ", "")
    tokens = trading_bot.user_states.get(message.chat.id, [])

    token_data = None
    for token in tokens:
        if token['symbol'] == symbol:
            token_data = token
            break

    if not token_data:
        await message.answer("❌ Токен не найден", reply_markup=get_back_keyboard())
        return

    if trading_bot.add_monitored_token(token_data, message.chat.id):
        await message.answer(f"✅ {token_data['symbol']} добавлен в отслеживание!", reply_markup=get_back_keyboard())
    else:
        await message.answer(f"⚠️ {token_data['symbol']} уже отслеживается!", reply_markup=get_back_keyboard())


@dp.message(F.text == "Back")
async def back_to_main(message: Message):
    await message.answer(
        "🤖 Trading Bot Activated\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )


async def periodic_tasks():
    while True:
        try:
            await trading_bot.run_scripts()
            await trading_bot.check_price_alerts()
        except Exception as e:
            print(f"Ошибка в периодических задачах: {e}")
        await asyncio.sleep(60)


async def main():
    asyncio.create_task(periodic_tasks())
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())