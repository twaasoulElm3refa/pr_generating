from fastapi import FastAPI, HTTPException
import mysql.connector
from mysql.connector import Error
from database import get_db_connection, fetch_press_releases, update_press_release
from pydantic import BaseModel
import openai
import os
import time
#from openai import OpenAI, RateLimitError
import faiss
import numpy as np
import json
from sentence_transformers import SentenceTransformer
import uvicorn 
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_article_based_on_topic(topic, corpus, index,lines_number,website):

    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    # Find relevant documents based on the topic embedding
    topic_embedding = model.encode([topic])
    D, I = index.search(np.array(topic_embedding), 3)  # Get top 3 related documents

    # Retrieve the content for those documents
    context = "\n".join([corpus[i]["content"] for i in I[0]])

    # Create the prompt for GPT
    prompt = f"""
أنت صحفي عربى محترف في مؤسسة إعلامية بارزة، ومتخصص في كتابة البيانات الإخبارية بلغة عربية فصيحة مع الالتزام بالبيانات والتفاصيل الممنوحة اليك وصياغتها فى صوره بيان مع الالتزام بعدد الاسطر {lines_number} معتمدا فى البيان على البيانات المدخله لك من المستخدم او مواقع رسميه ذات مصادر موثقه مائة باللمائة مع ذكر فى بدايه البيان العنوان الرئيسي و تاريخ اليوم حسب الوطن العربي ثم محتوى البيان ثم كلمة 'للمحررين'  ثم الحول ثم فى نهايه البيان بيانات التواصل من تليفون و ايميل و وسائل التواصل الاجتماعى (ان ذكرت فى التلقين او البيانات المدخله من المستخدم) دون تاليف او تعديل مع ترك مساحتها فارغه اذا لم يتم تحديدها من المستخدم: {topic}.
    استخدم المعلومات التالية كنموذج لكيقية صياغه المبيان :
    {context}
    و الرجوع الى موقعهم الموجود فى  {website} لكتابه حول عنهم من خدمات يقدموها الى من هم 
    """

    # Get response from OpenAI
    response  = openai.chat.completions.create(
      model="gpt-4o-mini",
      store=True,
      messages=[{"role": "user", "content": prompt}]
        )
    
    return response.choices[0].message.content.strip()

@app.get("/generate-article/{user_id}")
async def generate_article(user_id: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    user_session_id = user_id

    all_release = fetch_press_releases(user_session_id)
    release = all_release[-1]
    
    with open('filtered_corpus.json', 'r', encoding='utf-8') as json_file:
        corpus = json.load(json_file)
    index = faiss.read_index("my_index.index")

    # Prepare the Arabic prompt
    topic = f"اكتب بيان للشركة {release['organization_name']} حيث محتوى البيان عن {release['about_press']} وبيانات التواصل {release['organization_phone'],release['organization_email'],release['organization_website']} بتاريخ {release['press_date']} واذكر حول الشركه فى النهايه{release['about_organization']} ويكون عدد الاسطر {release['press_lines_number']}"

    article = generate_article_based_on_topic(topic, corpus, index,release['press_lines_number'],release['organization_website'])
    
    print(article)

    update_data= update_press_release(release['user_id'], release['organization_name'], article)
    print("update_data",update_data)
    connection.commit()
    cursor.close()
    connection.close()

    return {"generated_content":article}

if __name__ == "__main__":              
    uvicorn.run(app, host="66.29.132.81", port=443)