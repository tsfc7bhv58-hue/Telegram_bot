from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

async def notify_moderators_about_new_post(context: ContextTypes.DEFAULT_TYPE, post_id: int, username: str):
    message = f"🆕 Новое объявление на модерацию\nID: {post_id}\nОт: @{username}"
    for mod_id in MODERATOR_IDS:
        try:
            await context.bot.send_message(chat_id=mod_id, text=message)
        except Exception as e:
            print(f"Не удалось отправить уведомление модератору {mod_id}: {e}")