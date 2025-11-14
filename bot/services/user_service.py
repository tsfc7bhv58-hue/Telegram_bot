from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

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