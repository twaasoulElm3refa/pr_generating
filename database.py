# database.py
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

PR_TABLE = "wpl3_press_release_Form"
ARTICLES_TABLE = "wpl3_articles"

def get_db_connection():
    try:
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4",
            use_unicode=True,
            collation="utf8mb4_general_ci",
        )
        return cnx
    except Error as e:
        print(f"[DB] Connection error: {e}")
        return None

def fetch_release_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    """يجلب صفّ النموذج (المصدر) بحسب id (request_id)."""
    cnx = get_db_connection()
    if not cnx:
        return None
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute(f"""
            SELECT 
                id, user_id, organization_name, about_press, about_organization,
                organization_website, organization_phone, organization_email,
                press_lines_number, press_date
            FROM {PR_TABLE}
            WHERE id = %s
            LIMIT 1
        """, (request_id,))
        row = cur.fetchone()
        return row
    finally:
        cur.close()
        cnx.close()

def upsert_article_result(request_id: int, user_id: int, organization_name: str, article: str) -> bool:
    """
    يحفظ المقال الناتج في wpl3_articles:
    - إذا وجد سجل بنفس (request_id, user_id) → UPDATE
    - غير ذلك → INSERT
    """
    cnx = get_db_connection()
    if not cnx:
        return False

    try:
        cur = cnx.cursor(dictionary=True)

        cur.execute(f"""
            SELECT article_id 
            FROM {ARTICLES_TABLE}
            WHERE request_id = %s AND user_id = %s
            LIMIT 1
        """, (request_id, user_id))
        existing = cur.fetchone()

        if existing:
            cur.execute(f"""
                UPDATE {ARTICLES_TABLE}
                SET organization_name = %s,
                    article = %s,
                    date = CURRENT_DATE(),
                    time = CURRENT_TIME()
                WHERE article_id = %s
            """, (organization_name or '', article or '', existing["article_id"]))
        else:
            cur.execute(f"""
                INSERT INTO {ARTICLES_TABLE}
                    (request_id, user_id, organization_name, article, date, time)
                VALUES
                    (%s, %s, %s, %s, CURRENT_DATE(), CURRENT_TIME())
            """, (request_id, user_id, organization_name or '', article or ''))

        cnx.commit()
        return True

    except Error as e:
        print(f"[DB] Upsert error: {e}")
        return False
    finally:
        cur.close()
        cnx.close()
