import re
import random
import gspread
from datetime import datetime
from typing import Dict, Any, Optional, List
from oauth2client.service_account import ServiceAccountCredentials

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from difflib import SequenceMatcher

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# НАСТРОЙКИ
# =========================

STATE_WAIT_NAME = "wait_name"
STATE_IDLE = "idle"

GOOGLE_SHEETS_WEBHOOK = "https://script.google.com/macros/s/AKfycbxi2sXker_ofkg_DyQvwnIrNJuFcsCnB_qHlBwUwBJ9GFA59fhELEsdZag18Sb6kEzsEg/exec"
GOOGLE_SHEETS_NAME = "HR Bot Analytics"
GOOGLE_SHEETS_KB_WORKSHEET = "Обучение бота"
GOOGLE_CREDENTIALS_FILE = "credentials.json"

sessions: Dict[str, Dict[str, Any]] = {}

# =========================
# МЕНЮ
# =========================

MAIN_MENU = [
    "ДМС",
    "Магазин подарков",
    "Отгулы",
    "Корпоративный университет",
    "HighPer",
    "Вопросы по кадрам",
    "Не нашёл ответ"
]

SUB_MENUS = {
    "ДМС": [
        "Где найти номер полиса?",
        "План ДМС",
        "Как согласовать анализы?",
        "Как добавить врача?",
        "Как найти или выбрать врача?",
        "Где найти список клиник",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "Магазин подарков": [
        "Как списать бонусы?",
        "Как накопить бонусы?",
        "Как изменить сумму?",
        "Как купить сертификат?",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "Отгулы": [
        "Сколько у меня осталось отгулов?",
        "Когда отгулы сгорят?",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "Корпоративный университет": [
        "Пароль от КУ",
        "Оформить заявку на обучение",
        "Где найти курс",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "HighPer": [
        "Как войти в личный кабинет?",
        "Что делать, если забыли пароль",
        "Не нашёл ответ",
        "Главное меню"
    ]
}

# =========================
# ОТВЕТЫ (заполнишь позже)
# =========================

ANSWERS = {
    "Где найти номер полиса?": "ответ",
    "План ДМС": "ответ",
    "Как согласовать анализы?": "ответ",
    "Как добавить врача?": "ответ",
    "Как найти или выбрать врача?": "ответ",
    "Где найти список клиник": "ответ",

    "Как списать бонусы?": "ответ",
    "Как накопить бонусы?": "ответ",
    "Как изменить сумму?": "ответ",
    "Как купить сертификат?": "ответ",

    "Сколько у меня осталось отгулов?": "ответ",
    "Когда отгулы сгорят?": "ответ",

    "Пароль от КУ": "ответ",
    "Оформить заявку на обучение": "ответ",
    "Где найти курс": "ответ",

    "Как войти в личный кабинет?": "ответ",
    "Что делать, если забыли пароль": "ответ",
}

# =========================
# SMALL TALK
# =========================

SMALL_TALK = {
    "привет", "ок", "понял", "ясно", "ага", "спасибо", "норм", "хорошо"
}

# =========================
# SERVICE
# =========================

class MessageIn(BaseModel):
    session_id: str
    text: str


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_response(reply, quick_replies, state):
    return {
        "reply": reply,
        "quick_replies": quick_replies,
        "state": state,
    }


def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "name": "",
            "state": STATE_WAIT_NAME,
            "context": None,
        }
    return sessions[session_id]


# =========================
# NORMALIZATION + SEARCH
# =========================

def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str):
    return set(normalize(text).split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def score_text(query: str, target: str) -> int:
    query_tokens = tokenize(query)
    target_tokens = tokenize(target)

    score = 0

    overlap = len(query_tokens & target_tokens)
    score += overlap * 15

    if target_tokens.issubset(query_tokens):
        score += 40

    for q in query_tokens:
        for t in target_tokens:
            if similarity(q, t) > 0.8:
                score += 5

    return score


# =========================
# GOOGLE SHEETS
# =========================

def load_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEETS_NAME).worksheet(GOOGLE_SHEETS_KB_WORKSHEET)
        return sheet.get_all_records()
    except:
        return []


def search_sheet(text, context=None):
    rows = load_sheet()
    if not rows:
        return None

    best_score = 0
    best_answer = None

    for row in rows:
        status = str(row.get("Статус", "")).lower()
        if status not in ["ready", "added", "reviewed"]:
            continue

        row_topic = str(row.get("Тема", "")).strip()

        if context and row_topic:
            if normalize(context) not in normalize(row_topic):
                continue

        question = str(row.get("Вопрос сотрудника (как есть)", ""))
        keywords = str(row.get("Ключевые слова", ""))

        candidates = [question] + keywords.split(",")

        row_score = 0

        for c in candidates:
            row_score = max(row_score, score_text(text, c))

        if row_score > best_score:
            best_score = row_score
            best_answer = row.get("Ответ бота")

    if best_score >= 15:
        return best_answer

    return None


# =========================
# ЛОГИ
# =========================

def log_unknown_question(session, text):
    payload = {
        "timestamp": now_str(),
        "session_id": session.get("session_id"),
        "name": session.get("name"),
        "unknown_question": text
    }

    try:
        requests.post(GOOGLE_SHEETS_WEBHOOK, json=payload, timeout=3)
    except:
        pass


# =========================
# API
# =========================

@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/api/message")
def api_message(payload: MessageIn):
    session = get_session(payload.session_id)
    text = payload.text.strip()

    # старт
    if text == "__start__":
        session["state"] = STATE_WAIT_NAME
        return make_response(
            "Привет!\n\nЯ СиЭс — HR-ассистент.\n\nПомогу с адаптацией и отвечу на вопросы по компании.\n\nКак я могу к тебе обращаться?",
            [],
            STATE_WAIT_NAME
        )

    # имя
    if session["state"] == STATE_WAIT_NAME:
        session["name"] = text
        session["state"] = STATE_IDLE
        return make_response(
            f"{text}, приятно познакомиться!\n\nВыбери тему или задай вопрос.",
            MAIN_MENU,
            STATE_IDLE
        )

    # анти мусор
    if normalize(text) in SMALL_TALK:
        return make_response(
            "Если есть вопрос — напиши его или выбери тему 👇",
            MAIN_MENU,
            STATE_IDLE
        )

    # главное меню
    if text in MAIN_MENU:
        if text == "Не нашёл ответ":
            session["context"] = None
            return make_response("Напиши вопрос своими словами.", [], STATE_IDLE)

        session["context"] = text

        return make_response(
            f"Выбери вопрос по теме «{text}»:",
            SUB_MENUS.get(text, []),
            STATE_IDLE
        )

    # подменю
    if text in ANSWERS:
        return make_response(ANSWERS[text], MAIN_MENU, STATE_IDLE)

    if text == "Главное меню":
        session["context"] = None
        return make_response("Выбери раздел:", MAIN_MENU, STATE_IDLE)

    # поиск
    sheet_answer = search_sheet(text, session.get("context"))
    if sheet_answer:
        return make_response(sheet_answer, MAIN_MENU, STATE_IDLE)

    # fallback + лог
    log_unknown_question(session, text)

    return make_response(
        "Пока не нашёл точный ответ. Попробуй переформулировать или выбери тему 👇",
        MAIN_MENU,
        STATE_IDLE
    )