import os, uuid, time, jwt
from typing import Optional, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from openai import OpenAI  # ← use the new SDK style

from database import get_db_connection, fetch_press_releases, update_press_release

# -------------------------
# App & environment
# -------------------------
load_dotenv()

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
JWT_SECRET      = os.getenv("JWT_SECRET")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")
if not JWT_SECRET:
    raise RuntimeError("Missing JWT_SECRET")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI(title="Press API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Existing: generator
# -------------------------
def generate_article_based_on_topic(topic: str, context: str, release: dict) -> str:
    # Build a clean prompt with proper interpolation
    prompt = f"""
أنت صحفي عربي محترف في مؤسسة إعلامية بارزة، متخصص في كتابة البيانات الصحفية بلغة عربية فصيحة ودقيقة.
اكتب البيان بصيغة "تعلن شركة ..." وليس "أعلنت"، بصوت المؤسسة، والتزم بالبيانات والتفاصيل الممنوحة وصغها في صورة بيان.
عدد الأسطر المطلوب: {release.get('press_lines_number', 'غير محدد')}

تكوين البيان:
- العنوان الرئيسي + تاريخ اليوم بصيغة الوطن العربي.
- اعتمادًا على موضوع: {topic} بتاريخ: {release.get('press_date', 'غير محدد')}
- محتوى البيان.
- ثم مباشرة السطر "معلومات للمحررين".
- ثم في السطر التالي "حول الشركة": {release.get('about_organization', 'غير متوفر')}.
- وفي نهاية البيان بيانات التواصل دون تأليف:
  الهاتف: {release.get('organization_phone', 'غير متوفر')}
  البريد الإلكتروني: {release.get('organization_email', 'غير متوفر')}
  الموقع: {release.get('organization_website', 'غير متوفر')}

استخدم المعلومات التالية كنموذج لكيفية صياغة البيان (إرشادات بنية وصياغة):
{context}
""".strip()

    # Get response from OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

@app.get("/generate_article/{user_id}")
async def generate_article(user_id: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    user_session_id = user_id

    all_release = fetch_press_releases(user_session_id)
    if not all_release:
        cursor.close()
        connection.close()
        return {"error": "قائمة الإصدارات فارغة. لا يوجد بيانات."}
    else:
        release = all_release[-1]
        # Prepare the Arabic prompt inputs
        topic = (
            f"اكتب بيان للشركة {release.get('organization_name', 'غير محدد')} "
            f"حيث محتوى البيان عن {release.get('about_press', 'غير محدد')} "
            f"وبيانات التواصل "
            f"{release.get('organization_phone', 'غير متوفر')}, "
            f"{release.get('organization_email', 'غير متوفر')}, "
            f"{release.get('organization_website', 'غير متوفر')} "
            f"بتاريخ {release.get('press_date', 'غير محدد')} "
            f"واذكر «حول الشركة» في النهاية: {release.get('about_organization', 'غير متوفر')} "
            f"ويكون عدد الأسطر {release.get('press_lines_number', 'غير محدد')}"
        )
        
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

        article = generate_article_based_on_topic(topic, context, release)
        update_press_release(release['user_id'], release['organization_name'], article)

        connection.commit()
        cursor.close()
        connection.close()

        return {"generated_content": article}

# -------------------------
# NEW: chat session + chat (streaming)
# -------------------------

# --- models for the new routes ---
class SessionIn(BaseModel):
    user_id: int
    wp_nonce: Optional[str] = None

class SessionOut(BaseModel):
    session_id: str
    token: str

class VisibleValue(BaseModel):
    id: Optional[int] = None
    organization_name: Optional[str] = None
    about_press: Optional[str] = None
    press_date: Optional[str] = None
    # fields referenced in _values_to_context:
    organization_phone: Optional[str] = None
    organization_email: Optional[str] = None
    organization_website: Optional[str] = None
    about_organization: Optional[str] = None
    press_lines_number: Optional[str] = None
    article: Optional[str] = None

class ChatIn(BaseModel):
    session_id: str
    user_id: int
    message: str
    visible_values: List[VisibleValue] = Field(default_factory=list)

# --- helpers ---
def _make_jwt(session_id: str, user_id: int) -> str:
    payload = {
        "sid": session_id,
        "uid": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 2,  # 2 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def _verify_jwt(bearer: Optional[str]):
    if not bearer or not bearer.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = bearer.split(" ", 1)[1]
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def _values_to_context(values: List[VisibleValue]) -> str:
    if not values:
        return "لا توجد بيانات مرئية حالياً لهذا المستخدم."
    v = values[0]
    parts: List[str] = []
    if v.organization_name:
        parts.append(f"اسم المنظمة: {v.organization_name}")
    if v.about_press:
        parts.append(f"عن البيان: {v.about_press}")
    if v.press_date:
        parts.append(f"تاريخ البيان: {v.press_date}")
    if v.organization_phone:
        parts.append(f"الهاتف: {v.organization_phone}")
    if v.organization_email:
        parts.append(f"البريد: {v.organization_email}")
    if v.organization_website:
        parts.append(f"الموقع: {v.organization_website}")
    if v.about_organization:
        parts.append(f"حول المنظمة: {v.about_organization}")
    if v.press_lines_number:
        parts.append(f"عدد الأسطر المرغوب: {v.press_lines_number}")
    if v.article:
        article = v.article
        # قص المقال إذا كان طويلاً جداً
        if len(article) > 1200:
            article = article[:1200] + "…"
        parts.append(f"النص الحالي للمقال: {article}")
    return " | ".join(parts) if parts else "لا توجد تفاصيل كافية."

# --- routes ---
@app.post("/session", response_model=SessionOut)
def create_session(body: SessionIn):
    sid = str(uuid.uuid4())
    token = _make_jwt(sid, body.user_id)
    return SessionOut(session_id=sid, token=token)

@app.post("/chat")
def chat(body: ChatIn, authorization: Optional[str] = Header(None)):
    _verify_jwt(authorization)

    context = _values_to_context(body.visible_values)
    sys_prompt = (
        "أنت مساعد موثوق يجيب بالاعتماد على البيانات المرئية الحالية للمستخدم. "
        "إذا كانت المعلومة غير متوفرة في البيانات المرئية فاذكر ذلك صراحةً "
        "واقترح ما يمكن فعله للحصول عليها.\n\n"
        f"البيانات المرئية الحالية: {context}"
    )

    user_msg = body.message or ""

    def stream():
        # Chat Completions streaming
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": user_msg}
            ],
            stream=True
        )
        for chunk in response:
            if chunk.choices and getattr(chunk.choices[0].delta, "content", None):
                yield chunk.choices[0].delta.content

    return StreamingResponse(stream(), media_type="text/plain")
