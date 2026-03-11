import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================
# OPTIONAL GOOGLE SHEETS
# =========================
GSHEETS_ENABLED = False
worksheet = None

try:
    import gspread
    from google.oauth2.service_account import Credentials

    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "hr_bot_logs")

    if GOOGLE_SERVICE_ACCOUNT_JSON:
        import json

        creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open(GOOGLE_SHEET_NAME)

        try:
            worksheet = spreadsheet.worksheet("logs")
        except Exception:
            worksheet = spreadsheet.add_worksheet(title="logs", rows="1000", cols="20")
            worksheet.append_row(
                [
                    "timestamp",
                    "session_id",
                    "user_name",
                    "department",
                    "position",
                    "event_type",
                    "question_category",
                    "question_text",
                    "matched_keywords",
                    "bot_reply",
                ]
            )

        GSHEETS_ENABLED = True
except Exception as e:
    print(f"Google Sheets not enabled: {e}")
    GSHEETS_ENABLED = False


# =========================
# APP
# =========================
app = FastAPI(title="CS Medica HR Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # при необходимости потом можно ограничить доменом Tilda
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# IN-MEMORY SESSIONS
# =========================
sessions: Dict[str, Dict[str, Any]] = {}


# =========================
# MODELS
# =========================
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    quick_replies: List[str] = []


# =========================
# STATIC CONTENT
# =========================
MAIN_MENU = [
    "Адаптация",
    "Испытательный срок",
    "Моя роль",
    "Задать вопрос",
]

ADAPTATION_MENU = [
    "План на 1-й день",
    "План на 1-ю неделю",
    "План на 1 месяц",
    "Документы и доступы",
    "Назад в меню",
]

ROLE_MENU = [
    "Кратко о моей должности",
    "Что особенно важно",
    "Ожидания на испытательный срок",
    "Назад в меню",
]

QUESTION_CATEGORIES = [
    "Рабочие задачи",
    "Оформление и документы",
    "График и правила",
    "Другое",
    "Назад в меню",
]


ADAPTATION_CONTENT = {
    "План на 1-й день": (
        "Понял! Вот информация.\n\n"
        "В первый день важно:\n"
        "— познакомиться с командой и руководителем\n"
        "— получить базовые доступы\n"
        "— понять основные задачи на старт\n"
        "— уточнить план адаптации на ближайшие дни"
    ),
    "План на 1-ю неделю": (
        "Понял! Вот информация.\n\n"
        "В первую неделю важно:\n"
        "— разобраться в основных процессах\n"
        "— понять зону своей ответственности\n"
        "— познакомиться с ключевыми коллегами\n"
        "— уточнить ожидания на испытательный срок"
    ),
    "План на 1 месяц": (
        "Понял! Вот информация.\n\n"
        "В первый месяц важно:\n"
        "— войти в рабочий ритм\n"
        "— закрепить понимание задач и процессов\n"
        "— собрать вопросы по роли и приоритетам\n"
        "— свериться с руководителем по промежуточным ожиданиям"
    ),
    "Документы и доступы": (
        "Понял! Вот информация.\n\n"
        "По документам и доступам обычно важно проверить:\n"
        "— оформлены ли все кадровые документы\n"
        "— есть ли доступы к нужным системам\n"
        "— понятно ли, к кому обращаться по оргвопросам"
    ),
}

PROBATION_TEXT = (
    "Понял! Вот информация.\n\n"
    "Испытательный срок — это период, когда важно понять задачи, ожидания по роли, "
    "рабочие процессы и критерии успешной адаптации. По общему ориентиру важно:\n"
    "— понимать свои приоритеты\n"
    "— быть на связи с руководителем\n"
    "— вовремя задавать вопросы\n"
    "— отслеживать прогресс по задачам"
)

ROLE_CONTENT = {
    "Кратко о моей должности": (
        "Понял! Вот информация.\n\n"
        "Здесь бот может показывать краткое описание роли сотрудника на основе выбранной должности. "
        "Пока в пилоте можно использовать общий ориентир: твоя роль — понимать задачи, зону ответственности "
        "и ожидаемый результат по своей позиции."
    ),
    "Что особенно важно": (
        "Понял! Вот информация.\n\n"
        "Обычно особенно важно:\n"
        "— понять приоритеты по задачам\n"
        "— быстро уточнять непонятные моменты\n"
        "— не копить вопросы\n"
        "— синхронизироваться с руководителем по ожиданиям"
    ),
    "Ожидания на испытательный срок": (
        "Понял! Вот информация.\n\n"
        "На испытательном сроке обычно важно:\n"
        "— понять процессы и рабочие задачи\n"
        "— выйти на стабильное выполнение своей роли\n"
        "— показать вовлечённость и понимание приоритетов\n\n"
        "Точные ожидания по конкретной роли лучше уточнять у руководителя."
    ),
}


# =========================
# KNOWN Q&A
# =========================
KNOWN_QA = [
    {
        "keywords": ["испытательный срок", "испыталка"],
        "reply": PROBATION_TEXT,
    },
    {
        "keywords": ["первый день", "1-й день", "план на 1-й день"],
        "reply": ADAPTATION_CONTENT["План на 1-й день"],
    },
    {
        "keywords": ["первая неделя", "1-я неделя", "план на 1-ю неделю"],
        "reply": ADAPTATION_CONTENT["План на 1-ю неделю"],
    },
    {
        "keywords": ["1 месяц", "первый месяц", "план на 1 месяц"],
        "reply": ADAPTATION_CONTENT["План на 1 месяц"],
    },
    {
        "keywords": ["документы", "доступы"],
        "reply": ADAPTATION_CONTENT["Документы и доступы"],
    },
    {
        "keywords": ["моя роль", "роль", "должность"],
        "reply": (
            "Понял! Вот информация.\n\n"
            "В разделе «Моя роль» можно посмотреть краткое описание должности, "
            "что особенно важно и ожидания на испытательный срок."
        ),
    },
]


# =========================
# FALLBACK ROUTING
# =========================
MANAGER_KEYWORDS = [
    "задач",
    "задача",
    "приоритет",
    "приоритеты",
    "ожидани",
    "результат",
    "результаты",
    "роль",
    "обязанност",
    "ответственност",
    "kpi",
    "цель",
    "цели",
    "план работ",
    "как лучше делать",
    "как выполнять",
    "что важно в работе",
    "согласовать",
    "согласование",
    "руководител",
    "по работе",
    "рабочая задача",
    "рабочие задачи",
    "чем мне заниматься",
    "что мне делать",
]

HR_REPLY = (
    "Понял! Тут лучше обратиться к HR.\n\n"
    "HR поможет с организационными вопросами и подскажет следующий шаг."
)

MANAGER_REPLY = (
    "Понял! Тут лучше уточнить у твоего руководителя, это его зона ответственности."
)


# =========================
# HELPERS
# =========================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text


def create_session() -> Dict[str, Any]:
    return {
        "state": "ask_name",
        "name": None,
        "department": None,
        "position": None,
        "question_category": None,
        "awaiting_free_question": False,
    }


def get_session(session_id: Optional[str]) -> (str, Dict[str, Any]):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = create_session()
    return session_id, sessions[session_id]


def log_event(
    session_id: str,
    event_type: str,
    question_text: str = "",
    question_category: str = "",
    matched_keywords: str = "",
    bot_reply: str = "",
) -> None:
    session = sessions.get(session_id, {})
    row = [
        now_str(),
        session_id,
        session.get("name") or "",
        session.get("department") or "",
        session.get("position") or "",
        event_type,
        question_category,
        question_text,
        matched_keywords,
        bot_reply,
    ]

    if GSHEETS_ENABLED and worksheet is not None:
        try:
            worksheet.append_row(row)
        except Exception as e:
            print(f"Sheets logging error: {e}")


def match_known_answer(message: str) -> Optional[str]:
    text = normalize_text(message)
    for item in KNOWN_QA:
        for keyword in item["keywords"]:
            if keyword in text:
                return item["reply"]
    return None


def classify_question(message: str) -> Dict[str, Any]:
    text = normalize_text(message)
    matched = []

    for keyword in MANAGER_KEYWORDS:
        if keyword in text:
            matched.append(keyword)

    if matched:
        return {
            "route": "manager",
            "matched_keywords": matched,
            "reply": MANAGER_REPLY,
        }

    return {
        "route": "hr",
        "matched_keywords": [],
        "reply": HR_REPLY,
    }


def menu_reply() -> ChatResponse:
    return ChatResponse(
        session_id="",
        reply="Понял! Вот информация.\n\nВыбери раздел, с которым помочь.",
        quick_replies=MAIN_MENU,
    )


def build_main_menu_response(session_id: str) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        reply="Понял! Вот информация.\n\nВыбери раздел, с которым помочь.",
        quick_replies=MAIN_MENU,
    )


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
    return {"ok": True, "service": "CS Medica HR Assistant"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
@app.post("/api/message", response_model=ChatResponse)
def chat(payload: ChatRequest):
    session_id, session = get_session(payload.session_id)
    raw_message = payload.message.strip()
    message = normalize_text(raw_message)

    # ===== ONBOARDING =====
    if session["state"] == "ask_name":
        session["state"] = "ask_department"
        return ChatResponse(
            session_id=session_id,
            reply="Привет! Я Сиэс, HR-ассистент по адаптации 😊\n\nКак тебя зовут?",
            quick_replies=[],
        )

    if session["state"] == "ask_department":
        if not session["name"]:
            session["name"] = raw_message

        session["state"] = "ask_position"
        return ChatResponse(
            session_id=session_id,
            reply=f"Очень приятно, {session['name']}! В каком ты направлении или департаменте?",
            quick_replies=[],
        )

    if session["state"] == "ask_position":
        if not session["department"]:
            session["department"] = raw_message

        session["state"] = "main_menu"
        return ChatResponse(
            session_id=session_id,
            reply="Отлично! Подскажи, пожалуйста, какая у тебя должность?",
            quick_replies=[],
        )

    # Завершение знакомства
    if session["state"] == "main_menu" and not session["position"]:
        session["position"] = raw_message
        return ChatResponse(
            session_id=session_id,
            reply=(
                f"Спасибо! Теперь я немного лучше тебя знаю.\n\n"
                f"Понял! Вот информация.\n\n"
                f"Выбери раздел, с которым помочь."
            ),
            quick_replies=MAIN_MENU,
        )

    # ===== NAVIGATION =====
    if raw_message == "Назад в меню":
        session["awaiting_free_question"] = False
        session["question_category"] = None
        return build_main_menu_response(session_id)

    if raw_message == "Адаптация":
        return ChatResponse(
            session_id=session_id,
            reply="Понял! Вот информация.\n\nВыбери, что именно тебе нужно по адаптации.",
            quick_replies=ADAPTATION_MENU,
        )

    if raw_message in ADAPTATION_CONTENT:
        return ChatResponse(
            session_id=session_id,
            reply=ADAPTATION_CONTENT[raw_message],
            quick_replies=["Назад в меню"],
        )

    if raw_message == "Испытательный срок":
        return ChatResponse(
            session_id=session_id,
            reply=PROBATION_TEXT,
            quick_replies=["Назад в меню"],
        )

    if raw_message == "Моя роль":
        return ChatResponse(
            session_id=session_id,
            reply="Понял! Вот информация.\n\nВыбери, что именно показать по твоей роли.",
            quick_replies=ROLE_MENU,
        )

    if raw_message in ROLE_CONTENT:
        return ChatResponse(
            session_id=session_id,
            reply=ROLE_CONTENT[raw_message],
            quick_replies=["Назад в меню"],
        )

    if raw_message == "Задать вопрос":
        session["awaiting_free_question"] = False
        session["question_category"] = None
        return ChatResponse(
            session_id=session_id,
            reply="Понял! Вот информация.\n\nВыбери категорию вопроса.",
            quick_replies=QUESTION_CATEGORIES,
        )

    if raw_message in QUESTION_CATEGORIES:
        if raw_message == "Назад в меню":
            return build_main_menu_response(session_id)

        session["question_category"] = raw_message
        session["awaiting_free_question"] = True
        return ChatResponse(
            session_id=session_id,
            reply="Понял! Напиши свой вопрос одним сообщением.",
            quick_replies=[],
        )

    # ===== FREE QUESTION FLOW =====
    if session["awaiting_free_question"]:
        session["awaiting_free_question"] = False

        known_answer = match_known_answer(raw_message)
        if known_answer:
            log_event(
                session_id=session_id,
                event_type="known_answer",
                question_text=raw_message,
                question_category=session.get("question_category") or "",
                matched_keywords="known_answer",
                bot_reply=known_answer,
            )
            session["question_category"] = None
            return ChatResponse(
                session_id=session_id,
                reply=known_answer,
                quick_replies=["Задать вопрос", "Назад в меню"],
            )

        classification = classify_question(raw_message)
        bot_reply = classification["reply"]

        log_event(
            session_id=session_id,
            event_type="fallback_route",
            question_text=raw_message,
            question_category=classification["route"],
            matched_keywords=", ".join(classification["matched_keywords"]),
            bot_reply=bot_reply,
        )

        session["question_category"] = None
        return ChatResponse(
            session_id=session_id,
            reply=bot_reply,
            quick_replies=["Задать вопрос", "Назад в меню"],
        )

    # ===== DIRECT KNOWN Q&A OUTSIDE CATEGORY FLOW =====
    known_answer = match_known_answer(raw_message)
    if known_answer:
        log_event(
            session_id=session_id,
            event_type="known_answer_direct",
            question_text=raw_message,
            question_category="direct",
            matched_keywords="known_answer",
            bot_reply=known_answer,
        )
        return ChatResponse(
            session_id=session_id,
            reply=known_answer,
            quick_replies=["Назад в меню"],
        )

    # ===== DEFAULT: MAIN MENU =====
    return build_main_menu_response(session_id)