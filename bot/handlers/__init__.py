#bot/handlers/__init__.py
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from .start import start_handler, server_selection_handler, select_server, referral_status
from .ad_posting import add_handler, text_handler, photo_handler, add_command
from .vip import buy_vip_handler, vip_plan_handler, check_payment_handler, buy_vip_stub
from .moderation import moderate_handler, approve_handler, reject_handler, reject_reason_handler, list_pending
from .broadcast import broadcast_start_handler, broadcast_message_handler, broadcast_start
from .ban import ban_start_handler, ban_input_handler, unban_start_handler, unban_input_handler
from .fallback import unsupported_media_handler
from .buttons import button_callback_handler

def register_all_handlers(app: Application):
    # Команды
    app.add_handler(start_handler)
    app.add_handler(add_handler)
    app.add_handler(moderate_handler)
    app.add_handler(buy_vip_handler)
    app.add_handler(check_payment_handler)
    app.add_handler(ban_start_handler)
    app.add_handler(unban_start_handler)
    app.add_handler(broadcast_start_handler)
    app.add_handler(CommandHandler("ref", referral_status))

    # Callback-кнопки
    app.add_handler(server_selection_handler)
    app.add_handler(vip_plan_handler)
    app.add_handler(approve_handler)
    app.add_handler(reject_handler)
    app.add_handler(CallbackQueryHandler(button_callback_handler, pattern=r'^cmd_'))  # ← регистрируем здесь

    # Состояния
    app.add_handler(broadcast_message_handler, group=1)
    app.add_handler(reject_reason_handler, group=2)
    app.add_handler(ban_input_handler, group=3)
    app.add_handler(unban_input_handler, group=4)

    # Контент
    app.add_handler(text_handler)
    app.add_handler(photo_handler)
    app.add_handler(unsupported_media_handler)