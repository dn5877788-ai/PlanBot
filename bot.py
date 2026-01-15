# bot.py
import os
import json
from datetime import date
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.enums import ParseMode
from aiohttp import web

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"https://planbot-vjeu.onrender.com{WEBHOOK_PATH}"

DATA_FILE = "data.json"

# ============ ИНИЦИАЛИЗАЦИЯ ============
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# ============ ФУНКЦИИ РАБОТЫ С ДАННЫМИ ============
def load_data():
    """Загружает данные из файла"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, ValueError):
            return {}
    return {}

def save_data(data):
    """Сохраняет данные в файл"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass

def get_user_key(user_id):
    """Генерирует ключ для пользователя"""
    return f"user_{user_id}"

# ============ КОМАНДЫ ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Проверяем, что сообщение в теме форума
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return
    
    try:
        thread_id = message.message_thread_id
        if not thread_id:
            return
            
        # Получаем информацию о теме
        topic = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=thread_id
        )
        # Проверяем название темы
        if topic.name != "Планы":
            return
    except Exception as e:
        print(f"Ошибка при проверке темы: {e}")
        return

    # Отправляем приветственное сообщение
    await message.answer(
        "Привет! Просто напиши свой план (например: «Купить хлеб»), и я добавлю его с кнопками.\n\n"
        "✅ Выполнено — сохранит в отчёт за месяц\n"
        "❌ Удалить — просто сотрёт"
    )

# ============ ОСНОВНОЙ ОБРАБОТЧИК ============
@router.message()
async def add_plan(message: Message):
    """Обработчик добавления нового плана"""
    # Проверка, что сообщение содержит текст
    if not hasattr(message, 'text') or not message.text or not isinstance(message.text, str):
        return

    text = message.text.strip()
    if not text or text.startswith('/'):
        return

    # Проверка, что сообщение в теме форума
    if not hasattr(message, 'is_topic_message') or not message.is_topic_message:
        return

    thread_id = getattr(message, 'message_thread_id', None)
    if not thread_id:
        return

    try:
        # Получаем информацию о теме
        topic_info = await bot.get_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=thread_id
        )
        # Проверяем название темы
        if topic_info.name != "Планы":
            return
    except Exception as e:
        print(f"Ошибка при проверке темы для плана: {e}")
        return

    # --- Сохраняем план ---
    user_id = message.from_user.id
    data = load_data()
    user_key = get_user_key(user_id)

    # ✅ ИСПРАВЛЕНО: добавлено 'data' после 'in'
    if user_key not in 
        data[user_key] = {"active_plans": [], "completed_plans": []}

    new_plan = {
        "text": text,
        "date_added": str(date.today())
    }
    data[user_key]["active_plans"].append(new_plan)
    save_data(data)

    # Создаем кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{len(data[user_key]['active_plans'])-1}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_{len(data[user_key]['active_plans'])-1}")
        ]
    ])

    # Отправляем подтверждение
    await message.answer(
        f"📝 План добавлен:\n<b>{text}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

# ============ ОБРАБОТКА КНОПОК ============
@router.callback_query(lambda c: c.data and (c.data.startswith("done_") or c.data.startswith("del_")))
async def handle_action(callback: CallbackQuery):
    """Обработчик нажатия кнопок"""
    if not callback.message or not hasattr(callback.message, 'chat'):
        await callback.answer("Ошибка сообщения.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    thread_id = getattr(callback.message, 'message_thread_id', None)
    if not thread_id:
        await callback.answer("Работает только в темах.", show_alert=True)
        return

    try:
        # Получаем информацию о теме
        topic_info = await bot.get_forum_topic(
            chat_id=chat_id,
            message_thread_id=thread_id
        )
        # Проверяем название темы
        if topic_info.name != "Планы":
            await callback.answer("Бот работает только в теме «Планы».", show_alert=True)
            return
    except Exception as e:
        print(f"Ошибка при проверке темы для кнопок: {e}")
        await callback.answer("Не удалось проверить тему.", show_alert=True)
        return

    user_id = callback.from_user.id
    user_key = get_user_key(user_id)
    data = load_data()

    # ✅ ИСПРАВЛЕНО: добавлено 'data' после 'in'
    if user_key not in 
        await callback.answer("Нет активных планов.", show_alert=True)
        return

    action, index_str = callback.data.split("_", 1)
    try:
        index = int(index_str)
        active_plans = data[user_key]["active_plans"]
        if index < 0 or index >= len(active_plans):
            raise IndexError
        plan = active_plans.pop(index)
    except (ValueError, IndexError, KeyError) as e:
        print(f"Ошибка при обработке действия: {e}")
        await callback.answer("План устарел или уже удален.", show_alert=True)
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

# ============ ЭНДПОИНТЫ ============
async def trigger_cleanup(request):
    """Эндпоинт для очистки старых данных"""
    return web.Response(text="🧹 Очистка не требуется сейчас.")

# ============ ФУНКЦИИ ЗАПУСКА ============
async def on_startup(app):
    """Установка webhook при запуске"""
    try:
        # Используем фиксированный URL для Render
        await bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook успешно установлен: {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

# ============ ЗАПУСК ============
def main():
    """Основная функция запуска"""
    print("🚀 Запуск бота...")
    print(f"	PORT: {PORT}")
    print(f"	WEBHOOK_URL: {WEBHOOK_URL}")
    
    dp.include_router(router)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    app.router.add_get("/trigger-cleanup", trigger_cleanup)
    app.on_startup.append(on_startup)
    
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    # ✅ ИСПРАВЛЕНО: добавлены скобки для вызова функции
    main()
