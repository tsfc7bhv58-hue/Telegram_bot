import re
from config.settings import BOT_TOKEN, CHANNEL_ID, SERVERS, SERVER_CHANNELS, SERVER_INVITE_LINKS, MODERATOR_IDS, YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, YOO_KASSA_WEBHOOK_URL, DB_CONFIG

def is_spam_content(text: str) -> tuple[bool, str]:
    text = text.strip()
    if not text:
        return True, "Пустой текст."

    if re.search(r'https?://|www\.[^\s]+|t\.me/|vk\.com|wa\.me|@\w{3,}', text, re.IGNORECASE):
        return True, "Объявления со ссылками или упоминаниями запрещены."

    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 5:
        uppercase_count = sum(1 for c in letters if c.isupper())
        if uppercase_count / len(letters) > 0.7:
            return True, "Излишнее использование заглавных букв."

    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text))
    if emoji_count > 0 and emoji_count / len(text) > 0.5:
        return True, "Слишком много эмодзи."

    words = text.split()
    if len(text) < 10 or len(words) < 2:
        return True, "Объявление слишком короткое. Минимум 2 слова."

    if re.search(r'(8|\+7)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text):
        return True, "Номера телефонов запрещены в объявлениях."

    return False, ""

