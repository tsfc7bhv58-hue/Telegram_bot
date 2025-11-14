from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.db import Database
from config.settings import MODERATOR_IDS, SERVERS

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    user = db.fetch_all("SELECT server_id FROM users WHERE user_id = %s", (user_id,))

    if not user or user[0]['server_id'] is None:
        # Если юзера нет в базе — отправляем выбор сервера
        await select_server(update, context)  # ❗ Убедись, что функция определена
        return

    server_id = user[0]['server_id']
    server_name = SERVERS.get(server_id, f"Сервер {server_id}")

    welcome_text = (
        f"👋 <b>Привет! Вы в сервере: {server_name} [{server_id}]</b>\n\n"
        "Здесь вы можете:\n"
        "• <b>Выставить объявление о продаже или покупке игрового имущества</b>\n"
        "• <b>Прикрепить фото</b> к объявлению — просто отправьте его с описанием\n"
        "• <b>Получить VIP-статус</b> — увеличивает лимит и даёт приоритет\n\n"
        "📌 <b>Как это работает:</b>\n"
        "1. Нажмите «Выставить объявление» или /add\n"
        "2. Напишите текст (без ссылок, @, номеров)\n"
        "   — Или отправьте <b>фото с описанием</b>\n"
        "3. Объявление отправится на <b>модерацию</b>\n"
        "4. После одобрения — появится в канале\n\n"
        "💎 <b>Преимущества VIP:</b>\n"
        "• 10 объявлений в день (вместо 3)\n"
        "• Приоритет в модерации\n"
        "• Объявления с рамкой и значком 💎\n\n"
        "⚠️ <b>Строгие правила:</b>\n"
        "• Запрещена реклама <b>18+ контента</b>\n"
        "• Запрещена реклама <b>наркотиков, алкоголя, табака</b>\n"
        "• Запрещены <b>мошенничество, читы, взлом аккаунтов</b>\n"
        "• Запрещены <b>любые ссылки и упоминания</b> (@username, t.me, vk.com и др.)\n"
        "• Запрещены <b>номера телефонов и персональные данные</b>\n\n"
        "❗ Нарушение правил = бан без предупреждения.\n\n"
    )

    keyboard = [
        [InlineKeyboardButton("📢 Выставить объявление", callback_data="cmd_add")],
        [InlineKeyboardButton("💎 Купить VIP", callback_data="cmd_buy_vip")],
        [InlineKeyboardButton("🔄 Сменить сервер", callback_data="cmd_change_server")]
    ]

    if user_id in MODERATOR_IDS:
        welcome_text += "🛡️ <b>Для модераторов:</b> доступна кнопка модерации и управления пользователями.\n\n"
        keyboard.append([InlineKeyboardButton("🛡️ Модерация", callback_data="cmd_moderate")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

# ❗ Обязательно определи функцию select_server, если она нужна:
async def select_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Тут логика выбора сервера
    await update.message.reply_text("Выберите сервер...")