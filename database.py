import mysql.connector
from mysql.connector import Error
from datetime import timedelta
from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any

load_dotenv()  # يبحث عن .env في مجلد المشروع الحالي

api_key = os.getenv("OPENAI_API_KEY")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

PR_TABLE = "wpl3_press_release_Form"
ARTICLES_TABLE = "wpl3_articles"

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        if connection.is_connected():
            print("✅ Connected!")
            return connection
    except Error as e:
        print("❌ Failed.")
        print(f"Error connecting to MySQL: {e}")
        return None

def fetch_press_releases(user_id: str ):
    connection = get_db_connection()
    if connection is None:
        print("Failed to establish database connection")
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        query = f"""
        SELECT * 
        FROM {PR_TABLE}
        WHERE user_id = %s 
        """
        cursor.execute(query, (user_id,))

        # Fetch the first row
        all_user_articles = cursor.fetchall()

        return all_user_articles

    except Error as e:
        print(f"Error fetching data: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def fetch_release_by_id(request_id: int):
    """يجلب صفّ النموذج (المصدر) بحسب id (request_id)."""
    connection = get_db_connection()
    if not connection:
        return None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"""
            SELECT 
                id, user_id, organization_name, about_press, about_organization,
                organization_website, organization_phone, organization_email,
                press_lines_number, press_date
            FROM {PR_TABLE}
            WHERE id = %s
            LIMIT 1
        """, (request_id,))
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        connection.close()


def insert_press_release( user_id, organization_name, article, request_id=1):
    connection = get_db_connection()
    if connection is None:
        return False
    try:
        cursor = connection.cursor()
        query = f"""
        INSERT INTO {ARTICLES_TABLE} (request_id, user_id, organization_name, article)
        VALUES (%s, %s, %s,%s)
        ON DUPLICATE KEY UPDATE article = VALUES(article)
        """
        cursor.execute(query, (request_id, user_id, organization_name, article))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating data: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
