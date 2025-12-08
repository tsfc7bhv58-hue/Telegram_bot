#bot/handlers/moderation.py
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from config import MODERATOR_IDS, SERVERS, SERVER_CHANNELS, CHANNEL_ID
from database import db
from bot.utils import is_user_banned

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in MODERATOR_IDS:
        await (update.callback_query.answer("❌ У вас нет доступа.", show_alert=True)
               if update.callback_query else update.message.reply_text("❌ У вас нет доступа."))
        return

    msg = update.callback_query.message if update.callback_query else update.effective_message
    posts = db.fetch_all("""
        SELECT id, user_id, username, message_text, photo_file_id, caption, is_vip, server_id
        FROM pending_posts
        WHERE status = 'pending'
        ORDER BY is_vip DESC, id DESC
    """)

    if not posts:
        await msg.reply_text("Нет объявлений на модерацию.")
        return

    await msg.reply_text(f"📋 Найдено {len(posts)} объявление(ий):")
    for post in posts:
        server_name = SERVERS.get(post["server_id"], "Не выбран")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{post['id']}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{post['id']}")
            ]
        ])
        vip_tag = " 💎 VIP" if post["is_vip"] else ""
        caption = (
            f"ID: {post['id']}\n"
            f"Сервер: {server_name} [{post['server_id']}]\n"
            f"От: @{post['username']}{vip_tag}\n"
        )
        if post["photo_file_id"]:
            await msg.reply_photo(
                post["photo_file_id"],
                caption=(caption + (post['caption'] or ""))[:1024],
                reply_markup=keyboard
            )
        else:
            await msg.reply_text(
                caption + f"Текст: {post['message_text']}",
                reply_markup=keyboard
            )

async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in MODERATOR_IDS:
        await update.callback_query.answer("❌ У вас нет прав.", show_alert=True)
        return

    query = update.callback_query
    await query.answer()
    post_id = int(query.data.split('_')[1])

    post = db.fetch_all("""
        SELECT user_id, username, message_text, photo_file_id, caption, is_vip, server_id
        FROM pending_posts WHERE id = %s AND status = 'pending'
    """, (post_id,))

    if not post:
        try:
            await (query.edit_message_caption(caption="❌ Объявление уже обработано.")
                   if query.message.caption else query.edit_message_text("❌ Объявление уже обработано."))
        except:
            pass
        return

    post = post[0]
    server_id = post['server_id']
    channel_id = SERVER_CHANNELS.get(server_id, CHANNEL_ID)

    db.execute_query(
        "UPDATE pending_posts SET status = 'approved', moderated_at = NOW() WHERE id = %s",
        (post_id,)
    )

    is_vip = post['is_vip']
    username = post['username']
    if is_vip:
        border = "========================="
        header = f"💎 Объявление от @{username}\n"
        if post['photo_file_id']:
            caption = f"{border}\n{header}\n{post['caption']}\n{border}"
            sent = await context.bot.send_photo(chat_id=channel_id, photo=post['photo_file_id'], caption=caption)
        else:
            text = f"{border}\n{header}\n{post['message_text']}\n{border}"
            sent = await context.bot.send_message(chat_id=channel_id, text=text)
    else:
        if post['photo_file_id']:
            caption = f"📢 Объявление от @{username}:\n{post['caption']}"
            sent = await context.bot.send_photo(chat_id=channel_id, photo=post['photo_file_id'], caption=caption)
        else:
            text = f"📢 Объявление от @{username}:\n{post['message_text']}"
            sent = await context.bot.send_message(chat_id=channel_id, text=text)

    server_name = SERVERS.get(server_id, "Основной") if server_id else "Основной"
    print(f"✅ Объявление ID {post_id} опубликовано в канале сервера: {server_name} [{server_id or 'N/A'}]")

    db.execute_query("""
        INSERT INTO published_posts (user_id, username, message_text, photo_file_id, caption, channel_message_id, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """, (
        post['user_id'],
        post['username'],
        post['message_text'],
        post.get('photo_file_id'),
        post.get('caption'),
        sent.message_id
    ))

    try:
        await (query.edit_message_caption(caption="✅ Объявление одобрено и опубликовано!")
               if post['photo_file_id'] else query.edit_message_text("✅ Объявление одобрено и опубликовано!"))
    except Exception as e:
        print(f"Не удалось отредактировать сообщение: {e}")

async def reject_entry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in MODERATOR_IDS:
        await update.callback_query.answer("❌ У вас нет прав.", show_alert=True)
        return

    query = update.callback_query
    await query.answer()
    post_id = int(query.data.split('_')[1])
    context.user_data['rejecting_post_id'] = post_id
    await query.message.reply_text("📝 Укажите причину отклонения:")
    context.user_data['state'] = 'rejecting'

async def handle_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'rejecting':
        return

    reason = update.message.text.strip()
    post_id = context.user_data.get('rejecting_post_id')
    if not post_id:
        await update.message.reply_text("❌ Ошибка: не найдено объявление для отклонения.")
        return

    post = db.fetch_all("SELECT user_id, username FROM pending_posts WHERE id = %s AND status = 'pending'", (post_id,))
    if not post:
        await update.message.reply_text("❌ Объявление уже обработано или не найдено.")
        return

    user_id = post[0]['user_id']
    username = post[0]['username']
    db.execute_query(
        "UPDATE pending_posts SET status = 'rejected', moderation_reason = %s, moderated_at = NOW() WHERE id = %s",
        (reason, post_id)
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Ваше объявление отклонено.\nПричина: {reason}"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

    await update.message.reply_text(f"✅ Объявление от @{username} отклонено. Причина отправлена пользователю.")
    context.user_data.pop('state', None)
    context.user_data.pop('rejecting_post_id', None)

moderate_handler = CommandHandler("moderate", list_pending)
approve_handler = CallbackQueryHandler(approve_callback, pattern=r'^approve_\d+$')
reject_handler = CallbackQueryHandler(reject_entry_callback, pattern=r'^reject_\d+$')
reject_reason_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reject_reason)