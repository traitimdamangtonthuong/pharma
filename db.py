import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

load_dotenv(Path(__file__).resolve().parent / ".env")


def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "quan_ly_nha_thuoc"),
        charset="utf8mb4",
        connection_timeout=5,
        use_pure=True
    )

    return connection


if __name__ == "__main__":
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE(), VERSION()")
        result = cursor.fetchone()

        print("KET NOI MYSQL THANH CONG!")
        print("Database:", result[0])
        print("MySQL Version:", result[1])

    except Error as e:
        print("KET NOI MYSQL THAT BAI!")
        print("Chi tiet loi:", e)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()