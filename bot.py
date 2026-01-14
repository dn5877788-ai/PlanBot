# bot.py
import os
import json
from datetime import datetime, date
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.enums import ParseMode
from aiohttp import web

import openpyxl

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 8000))

DATA_FILE = "data.json"
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

# ============ ИНИЦИАЛИЗАЦИЯ ============
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# ============ ФУНКЦИИ РАБОТЫ С ДАННЫМИ ============
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass

def get_user_key(user_id):
    return f"user_{user_id}"

def is_current_month(d: str) -> bool:
    try:
        plan_date = datetime.strptime(d, "%Y-%m-%d").date()
        today = date.today()
        return plan_date.year == today.year and plan_date.month == today.month
    except (ValueError, TypeError):
        return False

def export_month_to_excel(year: int, month: int):
    data = load_data()
    filename = REPORTS_DIR / f"{year}-{month:02d}.xlsx"
    
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{year}-{month:02d}"
        ws.append(["Дата выполнения", "Пользователь ID", "План"])

        for user_key, user_data in data.items():
            completed_list = user_data.get("completed_plans", [])
            for item in completed_list:
                comp_date_str = item.get("date_completed", "")
                try:
                    comp_date = datetime.strptime(comp_date_str, "%Y-%m-%d").date()
                    if comp_date.year == year and comp_date.month == month:
                        ws.append([comp_date_str, user_key, item["text"]])
                except (ValueError, TypeError):
                    continue

        wb.save(filename)
        return filename
    except Exception:
        return None

def cleanup_old_data():
    data = load_data()
    today = date.today()

    for user_key in list(data.keys()):
        user_data = data[user_key]

        active = user_data.get("active_plans", [])
        user_data["active_plans"] = [
            p for p in active if is_current_month(p.get("date_added", ""))
        ]

        completed = user_data.get("completed_plans", [])
        user_data["completed_plans"] = [
            p for p in completed if is_current_month(p.get("date_completed", ""))
        ]

        if not user_data["active_plans"] and not user_data["completed_plans"]:
            del data[user_key]

    save_data(data)

# ============ КОМАНДЫ ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return
    
    try:
        thread_id = message.message_thread_id
        if not thread_id:
            return
            
        topic = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=thread_id
        )
        if topic.name != "Планы":
            return
    except Exception:
        return

    await message.answer(
        "Привет! Просто напиши свой план (например: «Купить хлеб»), и я добавлю его с кнопками.\n\n"
        "✅ Выполнено — сохранит в отчёт за месяц\n"
        "❌ Удалить — просто сотрёт"
    )

# ============ ОСНОВНОЙ ОБРАБОТЧИК ============
@router.message()
async def add_plan(message: Message):
    # Защита от не-текстовых сообщений
    if not hasattr(message, 'text') or not message.text or not isinstance(message.text, str):
        return

    text = message.text.strip()
    if not text or text.startswith('/'):
        return

    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return

    thread_id = getattr(message, 'message_thread_id', None)
    if not thread_id:
        return

    try:
        topic_info = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=thread_id
        )
        if topic_info.name != "Планы":
            return
    except Exception:
        return

    # --- Сохраняем план ---
    user_id = message.from_user.id
    data = load_data()
    user_key = get_user_key(user_id)

    if user_key not in 
    data[user_key] = {"active_plans": [], "completed_plans": []}

    new_plan = {
        "text": text,
        "date_added": str(date.today())
    }
    data[user_key]["active_plans"].append(new_plan)
    save_data(data)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{len(data[user_key]['active_plans'])-1}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_{len(data[user_key]['active_plans'])-1}")
        ]
    ])

    await message.answer(
        f"📝 План добавлен:\n<b>{text}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

# ============ ОБРАБОТКА КНОПОК ============
@router.callback_query(lambda c: c.data and (c.data.startswith("done_") or c.data.startswith("del_")))
async def handle_action(callback: CallbackQuery):
    if not callback.message or not hasattr(callback.message, 'chat'):
        await callback.answer("Ошибка сообщения.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    thread_id = getattr(callback.message, 'message_thread_id', None)
    if not thread_id:
        await callback.answer("Работает только в темах.", show_alert=True)
        return

    try:
        topic_info = await bot.get_forum_topic(chat_id=chat_id, message_thread_id=thread_id)
        if topic_info.name != "Планы":
            await callback.answer("Только в теме «Планы».", show_alert=True)
            return
    except Exception:
        await callback.answer("Не удалось проверить тему.", show_alert=True)
        return

    user_id = callback.from_user.id
    user_key = get_user_key(user_id)
    data = load_data()

    if user_key not in data:
        await callback.answer("Нет активных планов.", show_alert=True)
        return

    action, index_str = callback.data.split("_", 1)
    try:
        index = int(index_str)
        active_plans = data[user_key]["active_plans"]
        if index < 0 or index >= len(active_plans):
            raise IndexError
        plan = active_plans.pop(index)
    except (ValueError, IndexError, KeyError):
        await callback.answer("План устарел.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    if action == "done":
        plan["date_completed"] = str(date.today())
        if "completed_plans" not in data[user_key]:
            data[user_key]["completed_plans"] = []
        data[user_key]["completed_plans"].append(plan)
        await callback.message.edit_text("✅ Выполнено! Сохранено в отчёт.")
    elif action == "del":
        await callback.message.edit_text("❌ Удалено.")

    save_data(data)
    await callback.answer()

# ============ ЭНДПОИНТ ОЧИСТКИ ============
async def trigger_cleanup(request):
    today = date.today()
    if today.day == 1:
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year = today.year if today.month > 1 else today.year - 1
        export_month_to_excel(prev_year, prev_month)
        cleanup_old_data()
        return web.Response(text=f"✅ Экспорт {prev_year}-{prev_month:02d}.xlsx и очистка завершены.")
    else:
        cleanup_old_data()
        return web.Response(text="🧹 Очистка старых данных.")

# ============ ЗАПУСК ============
async def on_startup(app):
    host = os.getenv("RENDER_EXTERNAL_URL", "https://planbot-vjeu.onrender.com")
    webhook_url = f"{host}{WEBHOOK_PATH}"
    try:
        await bot.set_webhook(webhook_url)
    except Exception as e:
        print(f"Ошибка установки webhook: {e}")

def main():
    dp.include_router(router)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    app.router.add_get("/trigger-cleanup", trigger_cleanup)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
Fix: complete 'if user_key not in data' syntax
