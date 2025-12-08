#bot/handlers/broadcast.py
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from config import MODERATOR_IDS
from database import db

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATOR_IDS:
        return
    msg = "📤 Отправьте текст для массовой рассылки:"
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(msg)
    else:
        await update.message.reply_text(msg)
    context.user_data['state'] = 'awaiting_broadcast'

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATOR_IDS:
        return
    if context.user_data.get('state') != 'awaiting_broadcast':
        return

    context.user_data.pop('state', None)
    message_text = update.message.text.strip()
    if not message_text:
        await update.message.reply_text("❌ Текст не может быть пустым.")
        return

    users = db.fetch_all("SELECT user_id FROM users")
    if not users:
        await update.message.reply_text("📭 Нет пользователей для рассылки.")
        return

    success, fail = 0, 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=message_text)
            success += 1
        except Exception as e:
            fail += 1
            print(f"❌ Ошибка при отправке рассылки пользователю {user['user_id']}: {e}")

    await update.message.reply_text(
        f"✅ Рассылка завершена!\n"
        f"Успешно: {success}\n"
        f"Неудачно: {fail}"
    )

#Хендлеры
broadcast_start_handler = CommandHandler("broadcast", broadcast_start)
broadcast_message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)