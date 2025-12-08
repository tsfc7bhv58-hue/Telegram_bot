# bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import SERVERS

def get_start_keyboard(user_id: int, is_moderator: bool = False) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📢 Выставить объявление", callback_data="cmd_add")],
        [InlineKeyboardButton("💎 Купить VIP", callback_data="cmd_buy_vip")],
        [InlineKeyboardButton("🔄 Сменить сервер", callback_data="cmd_change_server")]
    ]
    if is_moderator:
        keyboard.append([InlineKeyboardButton("🛡️ Модерация", callback_data="cmd_moderate")])
        keyboard.append([InlineKeyboardButton("📢 Массовая рассылка", callback_data="cmd_broadcast")])
    return InlineKeyboardMarkup(keyboard)

def get_server_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    keyboard = []
    for server_id, name in SERVERS.items():
        keyboard.append([InlineKeyboardButton(f"{name} [{server_id}]", callback_data=f"server_{server_id}")])
    start = page * 8
    end = start + 8
    current_page = keyboard[start:end]
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="server_prev"))
    if end < len(keyboard):
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data="server_next"))
    if nav_buttons:
        current_page.append(nav_buttons)
    return InlineKeyboardMarkup(current_page)

def get_vip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 VIP на 7 дней — 49 ₽", callback_data="vip_plan_7")],
        [InlineKeyboardButton("✨ VIP на 14 дней — 99 ₽", callback_data="vip_plan_14")],
        [InlineKeyboardButton("💎 VIP на 30 дней — 149 ₽", callback_data="vip_plan_30")]
    ])

def get_moderation_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{post_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{post_id}")
        ]
    ])