import os
import json
from datetime import date
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.enums import ParseMode
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 10000))

DATA_FILE = "data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user_key(uid):
    return f"u{uid}"

@router.message(Command("start"))
async def start(m: Message):
    if not m.is_topic_message:
        return
    try:
        topic = await bot.get_forum_topic(m.chat.id, m.message_thread_id)
        if topic.name != "Планы":
            return
    except:
        return
    await m.answer("Напишите план, например: «Купить хлеб»")

@router.message()
async def add_plan(m: Message):
    if not m.text or not isinstance(m.text, str):
        return
    text = m.text.strip()
    if not text or text.startswith("/"):
        return
    if not m.is_topic_message:
        return
    try:
        topic = await bot.get_forum_topic(m.chat.id, m.message_thread_id)
        if topic.name != "Планы":
            return
    except:
        return

    data = load_data()
    uid = get_user_key(m.from_user.id)
    if uid not in 
        data[uid] = {"active": [], "done": []}

    plan = {"text": text, "date": str(date.today())}
    data[uid]["active"].append(plan)
    save_data(data)

    idx = len(data[uid]["active"]) - 1
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"d_{idx}"),
         InlineKeyboardButton(text="❌ Удалить", callback_data=f"x_{idx}")]
    ])
    await m.answer(f"📝 {text}", reply_markup=kb)

@router.callback_query(lambda c: c.data and (c.data.startswith("d_") or c.data.startswith("x_")))
async def cb(cbq: CallbackQuery):
    # Проверка темы
    if not cbq.message or not hasattr(cbq.message, 'message_thread_id'):
        return
    try:
        topic = await bot.get_forum_topic(cbq.message.chat.id, cbq.message.message_thread_id)
        if topic.name != "Планы":
            return
    except:
        return

    data = load_data()
    uid = get_user_key(cbq.from_user.id)
    if uid not in 
        await cbq.answer("Нет планов", show_alert=True)
        return

    action, idx_str = cbq.data.split("_", 1)
    try:
        idx = int(idx_str)
        plan = data[uid]["active"].pop(idx)
    except:
        await cbq.message.delete()
        return

    if action == "d":
        plan["done_at"] = str(date.today())
        data[uid].setdefault("done", []).append(plan)
        await cbq.message.edit_text("✅ Выполнено!")
    else:
        await cbq.message.edit_text("❌ Удалено.")

    save_data(data)
    await cbq.answer()

async def cleanup(request):
    return web.Response(text="OK")

async def on_startup(app):
    url = f"https://{os.getenv('RENDER_EXTERNAL_URL', 'planbot-vjeu.onrender.com')}{WEBHOOK_PATH}"
    await bot.set_webhook(url)

def main():
    dp.include_router(router)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    app.router.add_get("/trigger-cleanup", cleanup)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
