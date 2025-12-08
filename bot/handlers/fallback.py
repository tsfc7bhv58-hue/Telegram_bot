#bot/handlers/fallback.py
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram import Update

async def handle_unsupported_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_ad_text'):
        await update.message.reply_text("❌ Для объявления нужно отправить текст или фото. Видео и документы не поддерживаются.")

unsupported_media_handler = MessageHandler(
    filters.VIDEO | filters.Document.Category("application/zip"),
    handle_unsupported_media
)