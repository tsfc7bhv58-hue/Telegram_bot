#bot/handlers/buttons.py
from telegram import Update
from telegram.ext import ContextTypes
from config import MODERATOR_IDS
from .ad_posting import add_command
from .vip import buy_vip_stub
from .moderation import list_pending
from .broadcast import broadcast_start
from .start import select_server, referral_status

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    if data == "cmd_add":
        await query.message.reply_text("📩 Напишите текст вашего объявления:")
        context.user_data['awaiting_ad_text'] = True
    elif data == "cmd_buy_vip":
        await buy_vip_stub(update, context)
    elif data == "cmd_change_server":
        await select_server(update, context)
    elif data == "cmd_moderate":
        await list_pending(update, context)
    elif data == "cmd_broadcast":
        if user_id in MODERATOR_IDS:
            await broadcast_start(update, context)
        else:
            await query.message.reply_text("❌ У вас нет доступа к рассылке.")
    elif data == "cmd_ref":
        await referral_status(update, context)
    else:
        return