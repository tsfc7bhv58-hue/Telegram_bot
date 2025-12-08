#bot/handlers/ad_posting.py
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from bot.utils import check_and_handle_ban, ensure_vip_status, get_daily_post_count, notify_moderators_about_new_post
from bot.validators import is_spam_content
from database import db

from .broadcast import handle_broadcast_message
from .moderation import handle_reject_reason
from .ban import ban_handle_input, unban_handle_input
from .vip import create_yookassa_payment

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_and_handle_ban(update, user_id):
        return
    await update.message.reply_text("📩 Напишите текст вашего объявления:")
    context.user_data['awaiting_ad_text'] = True

async def handle_any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    #Обработка email
    if context.user_data.get('awaiting_email'):
        if text == "-":
            await update.message.reply_text("📱 Укажите номер телефона в формате +79991234567:")
            context.user_data['awaiting_phone'] = True
            context.user_data.pop('awaiting_email', None)
        else:
            db.execute_query("UPDATE users SET email = %s WHERE user_id = %s", (text, user_id))
            await update.message.reply_text("✅ Email сохранён.")
            days = context.user_data.get('vip_days', 7)
            price = context.user_data.get('vip_price', 49)
            desc = context.user_data.get('vip_desc', f"VIP на {days} дней")
            await create_yookassa_payment(update, context, user_id, days, price, desc)
            for key in ['awaiting_email', 'vip_days', 'vip_price', 'vip_desc']:
                context.user_data.pop(key, None)
        return

    #Обработка телефона
    if context.user_data.get('awaiting_phone'):
        if not text.startswith("+") or len(text) < 10:
            await update.message.reply_text("📱 Неверный формат. Пример: +79991234567")
            return
        db.execute_query("UPDATE users SET phone = %s WHERE user_id = %s", (text, user_id))
        await update.message.reply_text("✅ Телефон сохранён.")
        days = context.user_data.get('vip_days', 7)
        price = context.user_data.get('vip_price', 49)
        desc = context.user_data.get('vip_desc', f"VIP на {days} дней")
        await create_yookassa_payment(update, context, user_id, days, price, desc)
        for key in ['awaiting_phone', 'vip_days', 'vip_price', 'vip_desc']:
            context.user_data.pop(key, None)
        return

    #Обработка других состояний
    state = context.user_data.get('state')
    if state == 'awaiting_broadcast':
        return await handle_broadcast_message(update, context)
    if state == 'rejecting':
        return await handle_reject_reason(update, context)
    if state == 'awaiting_ban_target' or state == 'awaiting_ban_reason':
        return await ban_handle_input(update, context)
    if context.user_data.get('unban_step') == 'target':
        return await unban_handle_input(update, context)
    
    message_text = update.message.text.strip()

    if not message_text:
        await update.message.reply_text("❌ Текст не может быть пустым. Попробуйте снова:")
        context.user_data['awaiting_ad_text'] = True
        return

    is_spam, reason = is_spam_content(message_text)
    if is_spam:
        await update.message.reply_text(f"❌ {reason}Попробуйте снова:")
        context.user_data['awaiting_ad_text'] = True
        return

    #Получение server_id на момент создания объявления
    user_info = db.fetch_all("SELECT server_id FROM users WHERE user_id = %s", (user_id,))
    user_server_id = user_info[0]['server_id'] if user_info and user_info[0]['server_id'] is not None else None

    db.execute_query("""
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE username = VALUES(username)
    """, (user_id, username))

    is_vip = ensure_vip_status(user_id)
    daily_count = get_daily_post_count(user_id)
    max_posts = 10 if is_vip else 1

    if daily_count >= max_posts:
        msg = f"❌ Вы отправили {daily_count} из {max_posts} возможных объявлений сегодня."
        if not is_vip:
            msg += " Приобретите VIP-статус для увеличения лимита до 10 объявлений в день!"
        await update.message.reply_text(msg)
        return

    db.execute_query("""
        INSERT INTO pending_posts (user_id, username, message_text, is_vip, status, server_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, username, message_text, is_vip, 'pending', user_server_id))

    post_id = db.fetch_all("SELECT LAST_INSERT_ID() as id")[0]['id']
    await notify_moderators_about_new_post(context, post_id, username)
    await update.message.reply_text("✅ Объявление отправлено на модерацию!")
    context.user_data.pop('state', None)

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

    user_info = db.fetch_all("SELECT server_id FROM users WHERE user_id = %s", (user_id,))
    user_server_id = user_info[0]['server_id'] if user_info else None

    db.execute_query("""
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE username = VALUES(username)
    """, (user_id, username))

    is_vip = ensure_vip_status(user_id)
    daily_count = get_daily_post_count(user_id)
    max_posts = 10 if is_vip else 1

    if daily_count >= max_posts:
        msg = f"❌ Вы отправили {daily_count} из {max_posts} возможных объявлений сегодня."
        if not is_vip:
            msg += " Приобретите VIP-статус для увеличения лимита до 10 объявлений в день!"
        await update.message.reply_text(msg)
        return

    db.execute_query("""
        INSERT INTO pending_posts (user_id, username, message_text, photo_file_id, caption, is_vip, status, server_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, username, caption, photo_file_id, caption, is_vip, 'pending', user_server_id))

    post_id = db.fetch_all("SELECT LAST_INSERT_ID() as id")[0]['id']
    await notify_moderators_about_new_post(context, post_id, username)
    await update.message.reply_text("✅ Фотообъявление отправлено на модерацию!")

#Хендлеры
add_handler = CommandHandler("add", add_command)
text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_text)
photo_handler = MessageHandler(filters.PHOTO, handle_photo)