#bot/handlers/start.py
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardMarkup
from bot.keyboards import get_start_keyboard, get_server_keyboard
from bot.utils import ensure_vip_status
from .ad_posting import add_command
from .vip import buy_vip_stub
from .moderation import list_pending
from .broadcast import broadcast_start
from database import db
from config import SERVERS, SERVER_INVITE_LINKS, MODERATOR_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔍 Функция start вызвана!")
    user_id = update.effective_user.id
    if context.user_data.get('server_changed'):
        is_new_message = True
        selected_server_id = context.user_data.get('last_selected_server_id')
        invite_link = SERVER_INVITE_LINKS.get(selected_server_id)
        link_text = f"\n🔗 <a href='{invite_link}'>Перейти в канал сервера</a>\n" if invite_link else "\n"
    elif update.callback_query:
        is_new_message = False
        link_text = ""
    else:
        is_new_message = True
        link_text = ""

    user = db.fetch_all("SELECT server_id FROM users WHERE user_id = %s", (user_id,))
    if not user or user[0]['server_id'] is None:
        await select_server(update, context)
        return

    server_id = user[0]['server_id']
    server_name = SERVERS.get(server_id, f"Сервер {server_id}")

    is_moderator = user_id in MODERATOR_IDS

    welcome_text = (
        f"👋 <b>Привет! Вы в сервере: {server_name} [{server_id}]</b>\n"
        f"{link_text}"
        "Здесь вы можете:\n"
        "• <b>Выставить объявление о продаже или покупке игрового имущества</b>\n"
        "• <b>Прикрепить фото</b> к объявлению — просто отправьте его с описанием\n"
        "• <b>Получить VIP-статус</b> — увеличивает лимит и даёт приоритет\n"
        "📌 <b>Как это работает:</b>\n"
        "1. Нажмите «Выставить объявление» или /add\n"
        "2. Напишите текст (без ссылок, @, номеров)\n"
        "   — Или отправьте <b>фото с описанием</b>\n"
        "3. Объявление отправится на <b>модерацию</b>\n"
        "4. После одобрения — появится в канале\n"
        "💎 <b>Преимущества VIP:</b>\n"
        "• 10 объявлений в день (вместо 1)\n"
        "• Приоритет в модерации\n"
        "• Объявления с рамкой и значком 💎\n"
        "⚠️ <b>Строгие правила:</b>\n"
        "• Запрещена реклама <b>18+ контента</b>\n"
        "• Запрещена реклама <b>наркотиков, алкоголя, табака</b>\n"
        "• Запрещены <b>мошенничество, продажа читов, ИВ(игровой валюты)</b>\n"
        "• Запрещены <b>любые ссылки и упоминания</b> (@username, t.me, vk.com и др.)\n"
        "• Запрещены <b>номера телефонов и персональные данные</b>\n"
        "❗ Нарушение правил = бан без предупреждения.\n"
    )

    if is_moderator:
        welcome_text += "🛡️ <b>Для модераторов:</b> доступна кнопка модерации и управления пользователями.\n"

    reply_markup = get_start_keyboard(user_id, is_moderator=is_moderator)
    if is_new_message:
        await update.effective_message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def select_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = context.user_data.get('server_page', 0)
    reply_markup = get_server_keyboard(page)
    text = "Выберите ваш сервер:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def handle_server_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "server_prev":
        context.user_data['server_page'] = max(0, context.user_data.get('server_page', 0) - 1)
        await select_server(update, context)
        return
    elif data == "server_next":
        context.user_data['server_page'] = context.user_data.get('server_page', 0) + 1
        await select_server(update, context)
        return

    server_id = int(data.split('_')[1])
    user_id = update.effective_user.id
    db.execute_query("""
        INSERT INTO users (user_id, server_id)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE server_id = VALUES(server_id)
    """, (user_id, server_id))
    await query.edit_message_text(f"✅ Сервер выбран: {SERVERS[server_id]} [{server_id}]")
    context.user_data['server_changed'] = True
    context.user_data['last_selected_server_id'] = server_id
    await start(update, context)
    context.user_data.pop('server_changed', None)
    context.user_data.pop('last_selected_server_id', None)

#Хендлеры
start_handler = CommandHandler("start", start)
server_selection_handler = CallbackQueryHandler(handle_server_selection, pattern=r"^(server_\d+|server_prev|server_next)$")