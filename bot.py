import os
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
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

# ============ КОМАНДЫ ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Проверяем, что сообщение в теме "Планы"
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return
    
    try:
        thread_id = getattr(message, 'message_thread_id', None)
        if not thread_id:
            return
            
        topic = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=thread_id
        )
        if topic.name != "Планы":
            return
    except:
        return
        
    await message.answer("Привет! Напиши свой план, и я добавлю его с кнопками.\n\n✅ Выполнено\n❌ Удалить")

# ============ ОСНОВНОЙ ОБРАБОТЧИК ============
@router.message()
async def add_plan(message: Message):
    # Защита от пустых сообщений
    if not message.text or not isinstance(message.text, str):
        return
        
    text = message.text.strip()
    if not text or text.startswith('/'):
        return
    
    # Проверяем, что сообщение в теме "Планы"
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return
    
    try:
        thread_id = getattr(message, 'message_thread_id', None)
        if not thread_id:
            return
            
        topic = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=thread_id
        )
        if topic.name != "Планы":
            return
    except:
        return

    # Создаем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнено", callback_data="done"),
            InlineKeyboardButton(text="❌ Удалить", callback_data="delete")
        ]
    ])
    
    # Отправляем сообщение с кнопками
    await message.answer(f"📝 {text}", reply_markup=keyboard)

# ============ ОБРАБОТКА КНОПОК ============
@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    # Проверяем, что нажатие в теме "Планы"
    if not hasattr(callback.message, 'is_topic_message') or not callback.message.is_topic_message:
        await callback.answer("Бот работает только в теме «Планы».", show_alert=True)
        return
    
    try:
        thread_id = getattr(callback.message, 'message_thread_id', None)
        if not thread_id:
            await callback.answer("Бот работает только в темах.", show_alert=True)
            return
            
        topic = await bot.get_forum_topic(
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id
        )
        if topic.name != "Планы":
            await callback.answer("Бот работает только в теме «Планы».", show_alert=True)
            return
    except:
        await callback.answer("Ошибка проверки темы.", show_alert=True)
        return

    # Обработка нажатий кнопок
    if callback.data == "done":
        await callback.message.edit_text("✅ План выполнен!")
    elif callback.data == "delete":
        await callback.message.edit_text("❌ План удален.")
    
    await callback.answer()

# ============ ЗАПУСК ============
async def on_startup(app):
    # Этот код не нужен, так как мы устанавливаем webhook вручную
    pass

def main():
    dp.include_router(router)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
