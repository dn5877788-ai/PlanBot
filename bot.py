import os
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_PATH = "/webhook"
PORT = 10000

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Бот работает! Напишите план.")

@router.message()
async def add_plan(message: Message):
    # Проверка темы "Планы"
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return
    try:
        topic = await bot.get_forum_topic(message.chat.id, message.message_thread_id)
        if topic.name != "Планы":
            return
    except:
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data="done"),
         InlineKeyboardButton(text="❌ Удалить", callback_data="delete")]
    ])
    await message.answer(f"📝 {message.text}", reply_markup=kb)

@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    if callback.data == "done":
        await callback.message.edit_text("✅ Готово!")
    elif callback.data == "delete":
        await callback.message.edit_text("❌ Удалено.")
    await callback.answer()

def main():
    dp.include_router(router)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
