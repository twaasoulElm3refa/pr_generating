import os, uuid, time, jwt
from typing import Optional, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from openai import OpenAI

from database import get_db_connection, fetch_press_releases, update_press_release

# -------------------------
# App & environment
# -------------------------
load_dotenv()

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
JWT_SECRET      = os.getenv("JWT_SECRET", "change-me")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

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
    parts = []
    if v.organization_name: parts.append(f"اسم المنظمة: {v.organization_name}")
    if v.about_press:       parts.append(f"عن البيان: {v.about_press}")
    if v.press_date:        parts.append(f"تاريخ البيان: {v.press_date}")
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
            temperature=0.2,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": user_msg}
            ],
            stream=True
        )
        for chunk in response:
            delta = getattr(chunk.choices[0].delta, "content", None) if chunk.choices else None
            if delta:
                yield delta

    return StreamingResponse(stream(), media_type="text/plain")
