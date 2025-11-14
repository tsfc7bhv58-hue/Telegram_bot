from telegram import Update
from telegram.ext import ContextTypes
from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

async def select_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for server_id, name in SERVERS.items():
        keyboard.append([InlineKeyboardButton(f"{name} [{server_id}]", callback_data=f"server_{server_id}")])
    
    # Разбиваем на страницы по 8 серверов
    page = context.user_data.get('server_page', 0)
    start = page * 8
    end = start + 8
    current_page = keyboard[start:end]
    
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="server_prev"))
    if end < len(keyboard):
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data="server_next"))
    
    if nav_buttons:
        current_page.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(current_page)
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите ваш сервер:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Выберите ваш сервер:", reply_markup=reply_markup)

async def handle_server_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "server_prev":
        context.user_data['server_page'] = max(0, context.user_data.get('server_page', 0) - 1)
        await select_server(update, context)
        return
    elif query.data == "server_next":
        context.user_data['server_page'] = context.user_data.get('server_page', 0) + 1
        await select_server(update, context)
        return
    
    server_id = int(query.data.split('_')[1])
    user_id = update.effective_user.id
    
    # Сохраняем сервер
    db.execute_query("""
        INSERT INTO users (user_id, server_id)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE server_id = VALUES(server_id)
    """, (user_id, server_id))
    
    # Получаем пригласительную ссылку из config
    invite_link = SERVER_INVITE_LINKS.get(server_id, "Ссылка недоступна")
    server_name = SERVERS.get(server_id, f"Сервер {server_id}")
    
    message = f"✅ Сервер выбран: **{server_name} [{server_id}]**\n" \
              f"🔗 Присоединяйтесь к каналу: {invite_link}"

    # Отправляем ОТДЕЛЬНОЕ сообщение
    await query.message.reply_text(message, parse_mode="Markdown")
    
    # Показываем главное меню
    await start(update, context)