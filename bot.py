import os
import json
from datetime import date
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.enums import ParseMode
from aiohttp import web

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = "https://planbot-vjeu.onrender.com/webhook"

# ============ ИНИЦИАЛИЗАЦИЯ ============
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# ============ ОСНОВНАЯ ЛОГИКА ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Напиши свой план, и я добавлю его с кнопками.\n\n"
        "✅ Выполнено — сохранит в отчёт\n"
        "❌ Удалить — удалит план"
    )

@router.message()
async def add_plan(message: Message):
    # Проверка, что сообщение в теме "Планы"
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return
    try:
        topic = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id
        )
        if topic.name != "Планы":
            return
    except:
        return

    # Сохраняем план
    text = message.text.strip()
    if not text or text.startswith('/'):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнено", callback_data="done"),
            InlineKeyboardButton(text="❌ Удалить", callback_data="delete")
        ]
    ])
    await message.answer(f"📝 {text}", reply_markup=kb)

@router.callback_query()
async def handle_action(callback: CallbackQuery):
    # Проверка, что нажатие в теме "Планы"
    if not callback.message or not hasattr(callback.message, 'message_thread_id'):
        return
    try:
        topic = await bot.get_forum_topic(
            chat_id=callback.message.chat.id,
            message_thread_id=callback.message.message_thread_id
        )
        if topic.name != "Планы":
            return
    except:
        return

    # Обработка кнопок
    if callback.data == "done":
        await callback.message.edit_text("✅ Выполнено!")
    elif callback.data == "delete":
        await callback.message.edit_text("❌ Удалено.")

    await callback.answer()

# ============ ЗАПУСК ============
async def on_startup(app):
    try:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

def main():
    dp.include_router(router)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
