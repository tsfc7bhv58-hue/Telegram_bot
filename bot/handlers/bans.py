from telegram import Update
from telegram.ext import ContextTypes
from config.settings import MODERATOR_IDS
from bot.database.db import Database

db = Database()

def is_user_banned(user_id):
    """
    Проверяет, забанен ли пользователь по user_id.
    Возвращает (True, причина) или (False, None).
    """
    result = db.fetch_all("SELECT reason FROM banned_users WHERE user_id = %s", (user_id,))
    if result:
        return True, result[0]['reason']
    return False, None

async def check_and_handle_ban(update: Update, user_id: int) -> bool:
    """
    Проверяет, забанен ли пользователь.
    Если да — отправляет сообщение и возвращает True.
    """
    is_banned, reason = is_user_banned(user_id)
    if is_banned:
        await update.message.reply_text(f"❌ Вы забанены в этом боте.\nПричина: {reason}")
        return True
    return False

async def ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATOR_IDS:
        return
    await update.message.reply_text("Укажите user_id или username (без @) для бана:")
    context.user_data['state'] = 'awaiting_ban_target'

async def ban_handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATOR_IDS:
        return

    state = context.user_data.get('state')
    text = update.message.text.strip()

    if state == 'awaiting_ban_target':
        if text.startswith('@'):
            text = text[1:]
        context.user_data['ban_target'] = text
        await update.message.reply_text("Укажите причину бана:")
        context.user_data['state'] = 'awaiting_ban_reason'
        return

    if state == 'awaiting_ban_reason':
        reason = text
        target = context.user_data.get('ban_target')
        if not target:
            await update.message.reply_text("❌ Ошибка: не указан пользователь.")
            return

        user_id = None
        if target.isdigit():
            user_id = int(target)
            # Проверка: не модератор ли?
            if user_id in MODERATOR_IDS:
                await update.message.reply_text("❌ Нельзя забанить другого модератора.")
                return
            # Убедимся, что пользователь существует в БД
            db.execute_query("INSERT IGNORE INTO users (user_id) VALUES (%s)", (user_id,))
        else:
            user = db.fetch_all("SELECT user_id FROM users WHERE username = %s", (target,))
            if user:
                user_id = user[0]['user_id']
                if user_id in MODERATOR_IDS:
                    await update.message.reply_text("❌ Нельзя забанить другого модератора.")
                    return
            else:
                await update.message.reply_text(f"❌ Пользователь @{target} не найден (не отправлял объявлений).")
                return

        # Баним
        db.execute_query("""
            INSERT INTO banned_users (user_id, username, reason)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE reason = VALUES(reason)
        """, (user_id, target, reason))

        await update.message.reply_text(f"✅ Пользователь @{target} забанен.\nПричина: {reason}")

        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Вы забанены в боте объявлений.\nПричина: {reason}"
            )
        except Exception as e:
            print(f"Не удалось уведомить пользователя {user_id}: {e}")

        context.user_data.pop('state', None)
        context.user_data.pop('ban_target', None)
        return

    return

# === РАЗБАН ===
async def unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATOR_IDS:
        return
    await update.message.reply_text("📌 Укажите user_id или username (без @) для разбана:")
    context.user_data['unban_step'] = 'target'

async def unban_handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MODERATOR_IDS:
        return

    step = context.user_data.get('unban_step')
    if step != 'target':
        return

    text = update.message.text.strip()
    if text.startswith('@'):
        text = text[1:]

    # Ищем по user_id
    user_id = None
    username_to_show = text

    if text.isdigit():
        user_id = int(text)
        if user_id in MODERATOR_IDS:
            await update.message.reply_text("ℹ️ Этот пользователь — модератор, бан на него не распространяется.")
            context.user_data.pop('unban_step', None)
            return
        user = db.fetch_all("SELECT username FROM users WHERE user_id = %s", (user_id,))
        if user and user[0]['username']:
            username_to_show = user[0]['username']
    else:
        # Ищем по username
        user = db.fetch_all("SELECT user_id FROM banned_users WHERE username = %s", (text,))
        if user:
            user_id = user[0]['user_id']
        else:
            user = db.fetch_all("SELECT user_id FROM users WHERE username = %s", (text,))
            if user:
                user_id = user[0]['user_id']
            else:
                await update.message.reply_text(f"❌ Пользователь @{text} не найден.")
                return

    if not user_id:
        await update.message.reply_text("❌ Не удалось определить user_id.")
        return

    # Проверяем, забанен ли
    result = db.fetch_all("SELECT 1 FROM banned_users WHERE user_id = %s", (user_id,))
    if not result:
        await update.message.reply_text(f"ℹ️ Пользователь @{username_to_show} не забанен.")
    else:
        db.execute_query("DELETE FROM banned_users WHERE user_id = %s", (user_id,))
        await update.message.reply_text(f"✅ Пользователь @{username_to_show} разбанен.")

        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 Вы были разбанены в боте объявлений!\nТеперь вы снова можете публиковать объявления."
            )
        except Exception as e:
            print(f"Не удалось уведомить пользователя {user_id}: {e}")

    context.user_data.pop('unban_step', None)