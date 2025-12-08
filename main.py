#main.py
import logging
import traceback
from telegram.ext import Application, ContextTypes
from config import BOT_TOKEN
from database import db
from bot.handlers import register_all_handlers
from payments.jobs import setup_jobs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)

#Глобальный обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"❌ Ошибка при обработке обновления: {context.error}")
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)

def main():
    try:
        print("🔧 Попытка подключения к базе данных...")
        db.connect()
        print("✅ Подключение к БД успешно")

        print("⚙️ Создание приложения...")
        app = Application.builder().token(BOT_TOKEN).build()

        print("🔌 Регистрация хендлеров...")
        register_all_handlers(app)

        print("⏱️ Настройка задач...")
        setup_jobs(app.job_queue)

        #Регистрация error handler до запуска
        app.add_error_handler(error_handler)

        print("🤖 Бот запущен...")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print("💥 КРИТИЧЕСКАЯ ОШИБКА (на старте):")
        print(traceback.format_exc())
    finally:
        db.close()
        print("🔌 Соединение с БД закрыто")

if __name__ == '__main__':
    main()