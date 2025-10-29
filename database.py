import mysql.connector
from mysql.connector import Error
from datetime import timedelta
from dotenv import load_dotenv
import os
from typing import Optional, List, Dict, Any

load_dotenv()  # يبحث عن .env في مجلد المشروع الحالي

api_key = os.getenv("OPENAI_API_KEY")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

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

def _fetch_release_by_id(request_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(f"""
            SELECT id, user_id, organization_name, about_press, about_organization,
                   organization_website, organization_phone, organization_email,
                   press_lines_number, press_date
            FROM wpl3_press_release_Form
            WHERE id = %s
            LIMIT 1
        """, (request_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

def update_press_release(user_id, organization_name, article, request_id):
    connection = get_db_connection()
    if connection is None:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO wpl3_articles (request_id, user_id, organization_name, article, date, time)
            VALUES (%s, %s, %s, %s, CURRENT_DATE(), CURRENT_TIME())
            ON DUPLICATE KEY UPDATE
              organization_name = VALUES(organization_name),
              article           = VALUES(article),
              date              = VALUES(date),
              time              = VALUES(time)
        """, (request_id, user_id, organization_name or '', article or ''))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating data: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

'''def update_press_release(user_id, organization_name, article,request_id):
    connection = get_db_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        query = """
        INSERT INTO wpl3_articles (request_id,user_id, organization_name, article)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE article = VALUES(article)
        """
        cursor.execute(query, (request_id,user_id, organization_name, article))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating data: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()'''
