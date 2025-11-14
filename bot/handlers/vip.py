from telegram import Update
from telegram.ext import ContextTypes
from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

async def buy_vip_stub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем, есть ли активный VIP
    user = db.fetch_all("SELECT is_vip, vip_expires_at FROM users WHERE user_id = %s", (user_id,))
    if user and user[0]['is_vip'] and user[0]['vip_expires_at']:
        expires_at = user[0]['vip_expires_at']
        if expires_at > datetime.datetime.now():
            # VIP активен — считаем оставшиеся дни
            remaining = (expires_at - datetime.datetime.now()).days + 1
            message = (
                f"💎 У вас уже есть активный VIP-статус!\n"
                f"Осталось: **{remaining} день(дней)**.\n\n"
                "Вы не можете приобрести новый VIP, пока не закончится текущий."
            )
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")
            return

    # Если VIP нет — показываем тарифы
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("🔥 VIP на 7 дней — 49 ₽", callback_data="vip_plan_7")],
        [InlineKeyboardButton("✨ VIP на 14 дней — 99 ₽", callback_data="vip_plan_14")],
        [InlineKeyboardButton("💎 VIP на 30 дней — 149 ₽", callback_data="vip_plan_30")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "💎 <b>Выберите тариф VIP-статуса:</b>\n\n"
            "Все тарифы включают:\n"
            "• Лимит 10 объявлений/день (вместо 3)\n"
            "• Приоритет в модерации\n"
            "• Объявления с рамкой и значком 💎\n\n"
        ),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def handle_vip_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.split('_')[-1]
    user_id = update.effective_user.id
    
    user = db.fetch_all("SELECT is_vip, vip_expires_at FROM users WHERE user_id = %s", (user_id,))
    if user and user[0]['is_vip'] and user[0]['vip_expires_at']:
        expires_at = user[0]['vip_expires_at']
        if expires_at > datetime.datetime.now():
            # VIP активен — считаем оставшиеся дни
            remaining = (expires_at - datetime.datetime.now()).days + 1
            message = (
                f"💎 У вас уже есть активный VIP-статус!\n"
                f"Осталось: **{remaining} день(дней)**.\n\n"
                "Вы не можете приобрести новый VIP, пока не закончится текущий."
            )
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")
            return

    # Определяем параметры тарифа
    if plan == "7":
        price = "49.00"
        duration = 7
        desc = "VIP на 7 дней"
    elif plan == "14":
        price = "99.00"
        duration = 14
        desc = "VIP на 14 дней"
    elif plan == "30":
        price = "149.00"
        duration = 30
        desc = "VIP на 30 дней"
    else:
        await query.message.reply_text("❌ Неизвестный тариф.")
        return

    # Проверяем, есть ли у пользователя email или телефон
    user = db.fetch_all("SELECT email, phone FROM users WHERE user_id = %s", (user_id,))
    customer = {}
    if user and user[0]['email']:
        customer["email"] = user[0]['email']
    elif user and user[0]['phone']:
        customer["phone"] = user[0]['phone']
    else:
        # Если контакта нет — запрашиваем
        await query.message.reply_text(
            "📧 Для оплаты нужен email или телефон (для чека).\n"
            "Пожалуйста, пришлите email. Если нет — напишите «-», и я спрошу телефон."
        )
        context.user_data['awaiting_email'] = True
        context.user_data['vip_days'] = duration
        context.user_data['vip_price'] = price
        context.user_data['vip_desc'] = desc
        return

    # Создаём платёж
    payload = {
        "amount": {"value": price, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": f"https://t.me/{context.bot.username}"},
        "capture": True,
        "description": desc,
        "metadata": {"user_id": str(user_id), "days": str(duration)},
        "receipt": {
            "customer": customer,
            "items": [
                {
                    "description": desc,
                    "amount": {"value": price, "currency": "RUB"},
                    "quantity": 1,
                    "vat_code": 1,  # ← 1 = "Без НДС" для самозанятых
                    "payment_subject": "service",
                    "payment_mode": "full_payment"
                }
            ]
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.yookassa.ru/v3/payments",  # ← без пробелов!
                json=payload,
                auth=(YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY),
                headers={"Idempotence-Key": f"vip_{user_id}_{int(datetime.datetime.now().timestamp())}"}
            )
            data = response.json()
            if response.status_code == 200:
                confirmation_url = data["confirmation"]["confirmation_url"]
                real_payment_id = data["id"]  # ← НАСТОЯЩИЙ ID от ЮKassa

                # Сохраняем именно real_payment_id
                db.execute_query("""
                    INSERT INTO vip_payments (user_id, days, amount_rub, payment_id, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                """, (user_id, duration, price, real_payment_id))

                keyboard = [[InlineKeyboardButton("💳 Оплатить", url=confirmation_url)]]
                await query.message.reply_text(
                    f"💎 {desc}\n"
                    f"Цена: {price} ₽\n\n"
                    "Перейдите к оплате:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                print(f"❌ ЮKassa error: {response.status_code} - {data}")
                await query.message.reply_text("❌ Не удалось создать платёж. Проверьте настройки.")
    except Exception as e:
        print(f"❌ Exception in payment creation: {e}")
        await query.message.reply_text("❌ Ошибка при создании платежа. Попробуйте позже.")

# === ПРОВЕРКА ПЛАТЕЖА ===

async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    result = db.fetch_all("""
        SELECT payment_id FROM vip_payments
        WHERE user_id = %s AND status = 'pending'
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))

    if not result:
        await update.message.reply_text("❌ У вас нет активных платежей для проверки.")
        return

    payment_id = result[0]['payment_id']

    try:
        async with httpx.AsyncClient() as client:
            # 🔥 УБРАН ПРОБЕЛ В URL
            response = await client.get(
                f"https://api.yookassa.ru/v3/payments/{payment_id}",
                auth=(YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY)
            )
            data = response.json()
            if response.status_code == 200:
                status = data['status']
                if status == 'succeeded':
                    metadata = data['metadata']
                    days = int(metadata['days'])
                    expires = datetime.datetime.now() + datetime.timedelta(days=days)
                    db.execute_query("""
                        INSERT INTO users (user_id, is_vip, vip_expires_at)
                        VALUES (%s, TRUE, %s)
                        ON DUPLICATE KEY UPDATE is_vip = TRUE, vip_expires_at = %s
                    """, (user_id, expires, expires))
                    db.execute_query("UPDATE vip_payments SET status = 'succeeded' WHERE payment_id = %s", (payment_id,))
                    await update.message.reply_text(
                        "💎 Платёж подтверждён! Вам выдан VIP-статус.\n"
                        f"Срок: {days} дней. Наслаждайтесь!"
                    )
                elif status == 'pending':
                    await update.message.reply_text("⏳ Платёж всё ещё обрабатывается. Попробуйте позже.")
                elif status == 'canceled':
                    db.execute_query("UPDATE vip_payments SET status = 'canceled' WHERE payment_id = %s", (payment_id,))
                    await update.message.reply_text("❌ Платёж отменён.")
                else:
                    await update.message.reply_text(f"ℹ️ Статус платежа: {status}")
            else:
                print(f"❌ ЮKassa status check error: {response.status_code} - {data}")
                await update.message.reply_text("❌ Не удалось проверить статус платежа.")
    except Exception as e:
        print(f"❌ Ошибка при проверке платежа: {e}")
        await update.message.reply_text("❌ Ошибка при проверке платежа.")