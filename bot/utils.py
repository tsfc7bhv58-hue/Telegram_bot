# bot/utils.py
import datetime
from database import db
from config import MODERATOR_IDS

def get_daily_post_count(user_id: int) -> int:
    query = """
        SELECT COUNT(*) as count
        FROM pending_posts
        WHERE user_id = %s AND DATE(created_at) = CURDATE()
    """
    result = db.fetch_all(query, (user_id,))
    return result[0]['count'] if result else 0

def ensure_vip_status(user_id: int) -> bool:
    user = db.fetch_all("SELECT is_vip, vip_expires_at FROM users WHERE user_id = %s", (user_id,))
    if user and user[0]['is_vip'] and user[0]['vip_expires_at']:
        if user[0]['vip_expires_at'] < datetime.datetime.now():
            db.execute_query("UPDATE users SET is_vip = FALSE WHERE user_id = %s", (user_id,))
            return False
    return bool(user and user[0]['is_vip'])

def is_user_banned(user_id: int) -> tuple[bool, str]:
    result = db.fetch_all("SELECT reason FROM banned_users WHERE user_id = %s", (user_id,))
    if result:
        return True, result[0]['reason']
    return False, ""

async def check_and_handle_ban(update, user_id: int) -> bool:
    is_banned, reason = is_user_banned(user_id)
    if is_banned:
        await update.message.reply_text(f"❌ Вы забанены в этом боте.\nПричина: {reason}")
        return True
    return False

async def notify_moderators_about_new_post(context, post_id: int, username: str):
    from config import MODERATOR_IDS
    message = f"🆕 Новое объявление на модерацию\nID: {post_id}\nОт: @{username}"
    for mod_id in MODERATOR_IDS:
        try:
            await context.bot.send_message(chat_id=mod_id, text=message)
        except Exception as e:
            print(f"Не удалось отправить уведомление модератору {mod_id}: {e}")