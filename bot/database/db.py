import mysql.connector
from mysql.connector import Error
from config.settings import DB_CONFIG

class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("✅ Подключено к MariaDB")
        except Error as e:
            print(f"❌ Ошибка подключения: {e}")

    def execute_query(self, query, params=None):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
        except Error as e:
            print(f"❌ Ошибка выполнения запроса: {e}")
        finally:
            cursor.close()

    def fetch_all(self, query, params=None):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f"❌ Ошибка получения данных: {e}")
            return []
        finally:
            cursor.close()

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔌 Соединение закрыто")