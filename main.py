from fastapi import FastAPI
from database import get_db_connection,fetch_press_releases ,update_press_release
import os
from dotenv import load_dotenv
import uvicorn
import openai

app = FastAPI()

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")


def generate_article_based_on_topic(topic,context,release):
 
    # Create the prompt for GPT
    prompt = f"""انت صحفي عربي محترف في مؤسسة إعلامية بارزة ,متخصص فى كتابة البيانات الصحفية فى مختلف المواضيع بلغة عربية فصيحة ودقيقه .
    حيث يكون البيان بصيغة "تعلن شركة ..."وليس "اعلنت" وهكذا حيث تكون الصيغه على لسان المؤسسة مع الالتزام بالبيانات والتفاصيلئ الممنوحة اليك وصياغتها فى صوره بيان
    مع الالتزام بعدد الاسطر   release['press_lines_number']
    حيث يكون تكوين البيان :
    بدايه البيان العنوان الرئيسي و تاريخ اليوم حسب الوطن العربي 
     معتمدا فيه على {topic} release['press_date'] ثم محتوى البيان 
   "ثم كلمة "معلومات للمحررين
   "ثممباشرة فى السطر التالي كلمة "حول الشركة
   release['about_organization'] ثم 
فى نهايه البيان بيانات التواصل من تليفون و ايميل وموقع المؤسسة دون تاليف
release['organization_phone']
release['organization_email']
release['organization_website']
 استخدم المعلومات التالية كنموذج لكيقية صياغه البيان :
    {context}
 """  
   
    # Get response from OpenAI
    response  = openai.chat.completions.create(model="gpt-4o-mini",
                                               store=True,
                                               messages=[{"role": "user", "content": prompt}]
                                              )
    
    return response.choices[0].message.content.strip()
    

@app.get("/generate_article/{user_id}")
async def generate_article(user_id: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    user_session_id = user_id

    all_release = fetch_press_releases(user_session_id)
    if not all_release:
       return {"error": "قائمة الإصدارات فارغة. لا يوجد بيانات."}
       
    else:
       release = all_release[-1]
       # Prepare the Arabic prompt
       topic = f"اكتب بيان للشركة {release['organization_name']} حيث محتوى البيان عن {release['about_press']} وبيانات التواصل {release['organization_phone'],release['organization_email'],release['organization_website']} بتاريخ {release['press_date']} واذكر حول الشركه فى النهايه{release['about_organization']} ويكون عدد الاسطر {release['press_lines_number']}"
       context = f""" (Press Release Structure) الجزء الأول: الهيكلية العامة للبيان الصحفي
       1.	العنوان الرئيسي (Headline)
      الوظيفة: يجذب انتباه الصحفي والقارئ في أقل من 5 ثوانٍ.
      السمات: مباشر، مختصر، خبري، دون مبالغة، يعكس جوهر البيان.
      الطول الأمثل: 6–12 كلمة (يفضل أقل من 90 حرفًا).
      نموذج عالمي معتمد:
      بدلًا من: "حدث رائع وفريد من نوعه في السوق السعودي"
      استخدم: "شركة [X] تطلق أول منصة رقمية للتمويل العقاري في السعودية"
      2.	العنوان الفرعي (Subheadline) – اختياري
      الوظيفة: توسيع الفكرة الرئيسية، إضافة عنصر جديد (رقم، توقيت، فائدة).
      الطول الأمثل: لا يزيد عن سطرين.
      النبرة: معلوماتية، مكملة، دون تكرار العنوان الرئيسي.
      3.	سطر التاريخ (Dateline)
      الهيئة القياسية:
       [التاريخ الكامل بصيغة يوم/شهر/سنة]
      مثال:5 مايو 2025 
      4.	الفقرة الافتتاحية (Lead Paragraph)
      الوظيفة: تلخيص الخبر في جملة واحدة إلى ثلاث جمل.
      القاعدة الذهبية: الإجابة عن الأسئلة الست: من؟ ماذا؟ متى؟ أين؟ لماذا؟ كيف؟
      نغمة الصياغة: مباشرة، دون مقدمات أو سياقات تحليلية.
      5.	جسم البيان (Body)
      الفقرة الرابعة: تفاصيل إضافية .
      7.	معلومات التواصل (Media Contact)
      البريد الإلكتروني الرسمي
      رقم الهاتف المباشر
      8.	السطر الختامي (End Notation)
      يُفضل عالميًا استخدام:
      أو
      -	انتهى –
      لإعلام الصحفي بانتهاء البيان.
      الجزء الثاني: قواعد الصياغة الاحترافية لكل قسم في البيان الصحفي
      (Writing Best Practices by Section)
      1.	العنوان الرئيسي (Headline)
      أفضل الممارسات:
      ابدأ بالفعل أو الكلمة المفتاحية.
      تجنب الكلمات الإنشائية مثل: "متميز"، "رائع"، "فريد"، واستبدلها بمعلومة أو إنجاز ملموس.
      لا تضع نقطًا في نهاية العنوان.
      تجنب الحروف الكبيرة إلا في أسماء العلم أو الاختصارات الرسمية.
      مثال سيئ:
      "نجاح ساحق لشركتنا في إطلاق منتج مذهل"
      مثال احترافي:
      "شركة نماء تطلق أول منصة إلكترونية لتوزيع المنتجات الزراعية في الخليج"
      2.	العنوان الفرعي (Subheadline)
      أفضل الممارسات:
      يشرح قيمة أو نتيجة أو خلفية للعنوان.
      يضيف رقمًا أو إشارة زمنية أو توسيعًا جغرافيًا.
      لا يكرر كلمات العنوان.
      مثال جيد:
      "المنصة الجديدة توفر للمزارعين أدوات رقمية لتوسيع قاعدة عملائهم ورفع دخلهم بنسبة 30٪"
      3.	الفقرة الافتتاحية (Lead Paragraph)
      أفضل الممارسات:
      الصياغة كأنها خبر صحفي مستقل.
      دون تعبيرات ترحيبية أو مقدمات أدبية.
      لا تبدأ بـ"يسرّ الشركة" أو "أعلنت اليوم"، بل ابدأ بالحدث مباشرة.
      مثال جيد:
      "أطلقت شركة نماء اليوم منصتها الإلكترونية الجديدة التي تتيح للمزارعين بيع منتجاتهم مباشرةً للمستهلكين في مختلف مناطق الخليج."
      أخطاء شائعة:
      استخدام "نحن" أو ضمير المتكلم.
      التقديم الطويل قبل الدخول في الخبر.
      """
   
       article = generate_article_based_on_topic(topic,context, release)
   
       update_data= update_press_release(release['user_id'], release['organization_name'], article)
   
       connection.commit()
       cursor.close()
       connection.close()

       return {"generated_content":article}

