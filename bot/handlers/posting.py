from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.bans import check_and_handle_ban
from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG
def is_spam_content(text: str) -> tuple[bool, str]:
    spam_keywords = ["спам", "реклама", "ссылка", "bit.ly", "t.me/", "http"]
    for keyword in spam_keywords:
        if keyword.lower() in text.lower():
            return True, f"Обнаружен спам: {keyword}"
    return False, ""
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_and_handle_ban(update, user_id):
        return  # Если забанен — не даём начать
    await update.message.reply_text("📩 Напишите текст вашего объявления:")
    context.user_data['awaiting_ad_text'] = True

# === ОБРАБОТКА ТЕКСТА (включая сбор контакта) ===

async def handle_any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith('/'):
        return
    if update.message.from_user.id == context.bot.id:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"

    if await check_and_handle_ban(update, user_id):
        return

    if not context.user_data.get('awaiting_ad_text'):
        return

    context.user_data.pop('awaiting_ad_text', None)
    message_text = update.message.text.strip()
    if not message_text:
        await update.message.reply_text("❌ Текст не может быть пустым. Попробуйте снова:")
        context.user_data['awaiting_ad_text'] = True
        return

    is_spam, reason = is_spam_content(message_text)
    if is_spam:
        await update.message.reply_text(f"❌ {reason}\nПопробуйте снова:")
        context.user_data['awaiting_ad_text'] = True
        return

    # Сохраняем пользователя
    db.execute_query("""
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE username = VALUES(username)
    """, (user_id, username))

    # Получаем текущий server_id пользователя
    user_info = db.fetch_all("SELECT server_id FROM users WHERE user_id = %s", (user_id,))
    server_id = user_info[0]['server_id'] if user_info else None

    is_vip = ensure_vip_status(user_id)
    daily_count = get_daily_post_count(user_id)
    max_posts = 10 if is_vip else 3
    if daily_count >= max_posts:
        if is_vip:
            await update.message.reply_text(
                f"❌ Вы отправили {daily_count} из 10 возможных объявлений сегодня.\n"
                f"Лимит для VIP-пользователей — 10 объявлений в сутки."
            )
        else:
            await update.message.reply_text(
                f"❌ Вы отправили {daily_count} из 3 возможных объявлений сегодня.\n"
                f"Приобретите VIP-статус для увеличения лимита до 10 объявлений в день!"
            )
        return

    # Сохраняем объявление с server_id
    db.execute_query("""
        INSERT INTO pending_posts (user_id, username, message_text, is_vip, server_id, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
    """, (user_id, username, message_text, is_vip, server_id))

    post_id = db.fetch_all("SELECT LAST_INSERT_ID() as id")[0]['id']
    await notify_moderators_about_new_post(context, post_id, username)
    await update.message.reply_text("✅ Объявление отправлено на модерацию!")

    context.user_data.pop('awaiting_ad_text', None)
    context.user_data.pop('state', None)

# === ФОТО ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_and_handle_ban(update, user_id):
        return

    username = update.effective_user.username or "unknown"
    photo = update.message.photo[-1]
    photo_file_id = photo.file_id
    caption = (update.message.caption or "").strip() or "Без описания"

    is_spam, reason = is_spam_content(caption)
    if is_spam:
        await update.message.reply_text(f"❌ {reason}")
        return

    db.execute_query("""
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE username = VALUES(username)
    """, (user_id, username))

    # Получаем текущий server_id пользователя
    user_info = db.fetch_all("SELECT server_id FROM users WHERE user_id = %s", (user_id,))
    server_id = user_info[0]['server_id'] if user_info else None

    is_vip = ensure_vip_status(user_id)
    daily_count = get_daily_post_count(user_id)
    max_posts = 10 if is_vip else 3
    if daily_count >= max_posts:
        if is_vip:
            await update.message.reply_text(
                f"❌ Вы отправили {daily_count} из 10 возможных объявлений сегодня.\n"
                f"Лимит для VIP-пользователей — 10 объявлений в сутки."
            )
        else:
            await update.message.reply_text(
                f"❌ Вы отправили {daily_count} из 3 возможных объявлений сегодня.\n"
                f"Приобретите VIP-статус для увеличения лимита до 10 объявлений в день!"
            )
        return

    # Сохраняем объявление с server_id
    db.execute_query("""
        INSERT INTO pending_posts (user_id, username, message_text, photo_file_id, caption, is_vip, server_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
    """, (user_id, username, caption, photo_file_id, caption, is_vip, server_id))

    post_id = db.fetch_all("SELECT LAST_INSERT_ID() as id")[0]['id']
    await notify_moderators_about_new_post(context, post_id, username)
    await update.message.reply_text("✅ Фотообъявление отправлено на модерацию!")