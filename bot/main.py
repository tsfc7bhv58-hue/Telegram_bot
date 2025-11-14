import os
import sys
import warnings
import re
import datetime
import httpx
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

# Конфиг и база
from config.settings import BOT_TOKEN
from bot.database.db import Database

# Handlers
from bot.handlers.start import start
from bot.handlers.server import select_server, handle_server_selection
from bot.handlers.posting import add_command, handle_any_text, handle_photo
from bot.handlers.vip import buy_vip_stub, handle_vip_plan_selection, check_payment_status
from bot.handlers.moderation import list_pending, approve_callback, reject_entry_callback, handle_reject_reason
from bot.handlers.bans import ban_start, ban_handle_input, unban_start, unban_handle_input
from bot.handlers.callbacks import button_callback_handler


def main():
    db = Database()
    db.connect()

    app = Application.builder().token(BOT_TOKEN).build()

    # === Команды ===
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("moderate", list_pending))
    app.add_handler(CommandHandler("buy_vip", buy_vip_stub))
    app.add_handler(CommandHandler("check_payment", check_payment_status))
    app.add_handler(CommandHandler("ban", ban_start))
    app.add_handler(CommandHandler("unban", unban_start))

    # === Текст ===
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reject_reason), group=4)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ban_handle_input), group=10)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unban_handle_input), group=11)

    # === Фото ===
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # === Кнопки ===
    app.add_handler(CallbackQueryHandler(button_callback_handler, pattern=r'^cmd_'))
    app.add_handler(CallbackQueryHandler(handle_vip_plan_selection, pattern=r'^vip_plan_'))
    app.add_handler(CallbackQueryHandler(approve_callback, pattern=r'^approve_\d+$'))
    app.add_handler(CallbackQueryHandler(reject_entry_callback, pattern=r'^reject_\d+$'))
    app.add_handler(CallbackQueryHandler(handle_server_selection, pattern=r'^server_'))

    print("🤖 Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()