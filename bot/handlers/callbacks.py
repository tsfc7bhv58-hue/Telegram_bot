from telegram import Update
from telegram.ext import ContextTypes
from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

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
    else:
            return