# то как должен выглядеть settings.py
# Токен бота
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
CHANNEL_ID = -1001234567890
SERVERS = {
    1: "Server 1",
    2: "Server 2"
}

SERVER_CHANNELS = {
    1: -7891257617346,
    2: -1234567890101
}

SERVER_INVITE_LINKS = {
    1: "https://t.me/channels1",
    2: "https://t.me/channels2"
}


# ID модераторов
MODERATOR_IDS = [
    1234567890
    ]

# ЮKassa
YOO_KASSA_SHOP_ID = "1234567"
YOO_KASSA_SECRET_KEY = "live_An279329632as_2384812358xaf23355"

# Для WebHook(адреес не рабочий, это на будущее)
YOO_KASSA_WEBHOOK_URL = "https://yourdomain.com/yookassa_webhook"

# Конфигурация БД
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'admin',
    'database': 'database_name'
}