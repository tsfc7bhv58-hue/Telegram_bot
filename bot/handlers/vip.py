#bot/handlers/vip.py
import datetime
from datetime import timedelta
import httpx
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY
from bot.utils import ensure_vip_status
from payments.yookassa import create_payment

async def create_yookassa_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, days: int, price: str):
    last_payment = db.fetch_all("""
        SELECT created_at, status 
        FROM vip_payments 
        WHERE user_id = %s 
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    if last_payment:
        last_created = last_payment[0]['created_at']
        last_status = last_payment[0]['status']
        if last_status in ('pending', 'waiting_for_capture'):
            cooldown_expires = last_created + timedelta(minutes=PAYMENT_COOLDOWN_MINUTES)
            now = datetime.datetime.now()
            if now < cooldown_expires:
                remaining_minutes = int((cooldown_expires - now).total_seconds() // 60)
                await update.effective_message.reply_text(
                    f"⏳ Пожалуйста, подождите {remaining_minutes} минут(ы) перед созданием нового платежа."
                )
                return

    if days == 7:
        desc = "VIP на 7 дней"
    elif days == 14:
        desc = "VIP на 14 дней"
    elif days == 30:
        desc = "VIP на 30 дней"
    else:
        desc = f"VIP на {days} дней"

    user = db.fetch_all("SELECT email, phone FROM users WHERE user_id = %s", (user_id,))
    customer = {}
    if user and user[0]['email']:
        customer["email"] = user[0]['email']
    elif user and user[0]['phone']:
        customer["phone"] = user[0]['phone']
    else:
        await update.effective_message.reply_text("❌ Не удалось получить контакт для чека.")
        return

    payload = {
        "amount": {"value": price, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": f"https://t.me/{context.bot.username}"},
        "capture": True,
        "description": desc,
        "metadata": {"user_id": str(user_id), "days": str(days)},
        "receipt": {
            "customer": customer,
            "items": [
                {
                    "description": desc,
                    "amount": {"value": price, "currency": "RUB"},
                    "quantity": 1,
                    "vat_code": 1,
                    "payment_subject": "service",
                    "payment_mode": "full_payment"
                }
            ]
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.yookassa.ru/v3/payments",
                json=payload,
                auth=(YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY),
                headers={"Idempotence-Key": f"vip_{user_id}_{int(datetime.datetime.now().timestamp())}"}
            )
            data = response.json()
            if response.status_code == 200:
                confirmation_url = data["confirmation"]["confirmation_url"]
                real_payment_id = data["id"]
                db.execute_query("""
                    INSERT INTO vip_payments (user_id, days, amount_rub, payment_id, status, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', NOW())
                """, (user_id, days, price, real_payment_id))

                keyboard = [[InlineKeyboardButton("💳 Оплатить", url=confirmation_url)]]
                await update.effective_message.reply_text(
                    f"💎 {desc}\n"
                    f"Цена: {price} ₽\n"
                    "После оплаты напишите /check_payment для активации VIP.\n"
                    "Перейдите к оплате:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                print(f"❌ ЮKassa error: {response.status_code} - {data}")
                await update.effective_message.reply_text("❌ Не удалось создать платёж. Проверьте настройки.")
    except Exception as e:
        print(f"❌ Exception in create_yookassa_payment: {e}")
        await update.effective_message.reply_text("❌ Ошибка при создании платежа. Попробуйте позже.")
        
async def buy_vip_stub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.fetch_all("SELECT is_vip, vip_expires_at FROM users WHERE user_id = %s", (user_id,))
    if user and user[0]['is_vip'] and user[0]['vip_expires_at']:
        expires_at = user[0]['vip_expires_at']
        if expires_at > datetime.datetime.now():
            remaining = (expires_at - datetime.datetime.now()).days + 1
            message = (
                f"💎 У вас уже есть активный VIP-статус!\n"
                f"Осталось: **{remaining} день(дней)**.\n"
                "Вы не можете приобрести новый VIP, пока не закончится текущий."
            )
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")
            return

    chat_id = update.callback_query.message.chat_id if update.callback_query else update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("🔥 VIP на 7 дней — 49 ₽", callback_data="vip_plan_7")],
        [InlineKeyboardButton("✨ VIP на 14 дней — 99 ₽", callback_data="vip_plan_14")],
        [InlineKeyboardButton("💎 VIP на 30 дней — 149 ₽", callback_data="vip_plan_30")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "💎 <b>Выберите тариф VIP-статуса:</b>\n"
            "Все тарифы включают:\n"
            "• Лимит 10 объявлений/день (вместо 1)\n"
            "• Приоритет в модерации\n"
            "• Объявления с рамкой и значком 💎\n"
        ),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def handle_vip_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.split('_')[-1]
    user_id = update.effective_user.id

    plan_map = {
        "7": ("49.00", 7, "VIP на 7 дней"),
        "14": ("99.00", 14, "VIP на 14 дней"),
        "30": ("149.00", 30, "VIP на 30 дней"),
    }
    if plan not in plan_map:
        await query.message.reply_text("❌ Неизвестный тариф.")
        return

    price, duration, desc = plan_map[plan]

    last_payment = db.fetch_all("""
        SELECT created_at, status 
        FROM vip_payments 
        WHERE user_id = %s 
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    if last_payment:
        last_created = last_payment[0]['created_at']
        last_status = last_payment[0]['status']
        if last_status in ('pending', 'waiting_for_capture'):
            cooldown_expires = last_created + timedelta(minutes=10)
            now = datetime.datetime.now()
            if now < cooldown_expires:
                remaining_minutes = int((cooldown_expires - now).total_seconds() // 60)
                await query.message.reply_text(
                    f"⏳ Пожалуйста, подождите {remaining_minutes} минут(ы) перед созданием нового платежа."
                )
                return

    user = db.fetch_all("SELECT email, phone FROM users WHERE user_id = %s", (user_id,))
    customer = {}
    if user and user[0]['email']:
        customer["email"] = user[0]['email']
    elif user and user[0]['phone']:
        customer["phone"] = user[0]['phone']
    else:
        await query.message.reply_text(
            "📧 Для оплаты нужен email или телефон.\n"
            "Пожалуйста, пришлите email. Если нет — напишите «-», и я спрошу телефон."
        )
        context.user_data['awaiting_email'] = True
        context.user_data['vip_days'] = duration
        context.user_data['vip_price'] = price
        return

    from payments.yookassa import create_payment
    try:
        metadata = {"user_id": str(user_id), "days": str(duration)}
        result, status_code = await create_payment(
            amount=price,
            description=desc,
            customer=customer,
            return_url=f"https://t.me/{context.bot.username}",
            metadata=metadata
        )
        if status_code == 200:
            confirmation_url = result["confirmation"]["confirmation_url"]
            real_payment_id = result["id"]
            db.execute_query("""
                INSERT INTO vip_payments (user_id, days, amount_rub, payment_id, status, created_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW())
            """, (user_id, duration, price, real_payment_id))

            keyboard = [[InlineKeyboardButton("💳 Оплатить", url=confirmation_url)]]
            await query.message.reply_text(
                f"💎 {desc}\n"
                f"Цена: {price} ₽\n"
                "После оплаты напишите /check_payment для активации VIP.\n"
                "Перейдите к оплате:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            print(f"❌ ЮKassa error: {status_code} - {result}")
            await query.message.reply_text("❌ Не удалось создать платёж. Проверьте настройки.")
    except Exception as e:
        print(f"❌ Exception in payment creation: {e}")
        await query.message.reply_text("❌ Ошибка при создании платежа. Попробуйте позже.")

async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from payments.yookassa import check_payment
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
        data, status_code = await check_payment(payment_id)
        if status_code == 200:
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
            print(f"❌ ЮKassa status check error: {status_code} - {data}")
            await update.message.reply_text("❌ Не удалось проверить статус платежа.")
    except Exception as e:
        print(f"❌ Ошибка при проверке платежа: {e}")
        await update.message.reply_text("❌ Ошибка при проверке платежа.")

buy_vip_handler = CommandHandler("buy_vip", buy_vip_stub)
vip_plan_handler = CallbackQueryHandler(handle_vip_plan_selection, pattern=r'^vip_plan_')
check_payment_handler = CommandHandler("check_payment", check_payment_status)