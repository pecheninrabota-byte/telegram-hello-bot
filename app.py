import re
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATE_WAIT_NAME = "wait_name"
STATE_IDLE = "idle"

sessions: Dict[str, Dict[str, Any]] = {}

MAIN_MENU = [
    "ДМС",
    "Магазин подарков",
    "Отгулы",
    "Корпоративный университет",
    "HighPer",
    "1С личный кабинет",
    "Вопросы по кадрам",
    "Не нашёл ответ"
]

SUB_MENUS = {
    "ДМС": [
        "Где найти номер полиса?",
        "План ДМС",
        "Как согласовать анализы?",
        "Как найти или выбрать врача?",
        "Где найти список клиник",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "Магазин подарков": [
        "Как найти магазин бонусов",
        "Как списать бонусы?",
        "Как накопить бонусы?",
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
        "КУ: вход в личный кабинет",
        "КУ: забыли пароль",
        "Оформить заявку на обучение",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "HighPer": [
        "Что такое HighPer?",
        "HighPer: вход в личный кабинет",
        "HighPer: забыли пароль",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "1С личный кабинет": [
        "Что такое 1С личный кабинет сотрудника?",
        "Вход в личный кабинет",
        "Регистрация личного кабинета",
        "Установка мобильного приложения",
        "Настройка уведомления",
        "Подписание документов",
        "Перевыпуск электронной подписи",
        "Не нашёл ответ",
        "Главное меню"
    ]
}

ANSWERS = {

    # МАГАЗИН
    "Как найти магазин бонусов":
    """Магазин бонусов находится в Битрикс24:
https://bitrix.csdeskwork.ru/bonus/shop/""",

    "Как списать бонусы?":
    """Выбираешь товар → нажимаешь "получить".

После этого приходит сообщение от Вольф Марии.

Важно:
кроме Ozon — сначала платишь сам,
10 числа деньги возвращаются в зарплату.""",

    "Как накопить бонусы?":
    """Способы накопления:

• Спорт (забеги, шаги)
• Наставничество
• Приведи друга
• Праздники
• Юбилеи""",

    "Как купить сертификат?":
    """Сертификат Ozon приходит 15 или 30 числа.

Ссылка:
https://bitrix.csdeskwork.ru/bonus/shop/""",

    # ДМС
    "Где найти номер полиса?":
    """В приложении ИНГОССТРАХ:
https://www.ingos.ru/

Подробно:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "План ДМС":
    """В приложении ИНГОССТРАХ:
https://www.ingos.ru/""",

    "Как согласовать анализы?":
    """Анализы согласует врач после приема.

Уведомление придет в приложение ИНГОССТРАХ.""",

    "Как найти или выбрать врача?":
    """Через приложение ИНГОССТРАХ:
https://www.ingos.ru/""",

    "Где найти список клиник":
    """Список приходит на почту при подключении ДМС.""",

    # ОТГУЛЫ
    "Сколько у меня осталось отгулов?":
    """Смотри в Битрикс:
https://bitrix.csdeskwork.ru/page/reestr_otgulov/spisok/type/1056/list/category/14/""",

    "Когда отгулы сгорят?":
    """Смотри там же:
https://bitrix.csdeskwork.ru/page/reestr_otgulov/spisok/type/1056/list/category/14/""",

    # КУ
    "КУ: вход в личный кабинет":
    """Логин и пароль пришли в первый день.

Ссылка:
https://bitrix.csdeskwork.ru/knowledge/otgul/""",

    "КУ: забыли пароль":
    """Нажми "забыли пароль" на странице входа.""",

    "Оформить заявку на обучение":
    """Напиши Ефремовой Надежде в Битрикс.""",

    # HIGHPER
    "Что такое HighPer?":
    """Система KPI:
https://csmedica.highper.ru/Account/Login?ReturnUrl=%2f""",

    "HighPer: вход в личный кабинет":
    """Данные приходят после испытательного срока.

Вход:
https://csmedica.highper.ru/Account/Login?ReturnUrl=%2f""",

    "HighPer: забыли пароль":
    """Используй кнопку "забыл пароль".""",

    # 1С
    "Что такое 1С личный кабинет сотрудника?":
    """КЭДО для кадровых документов.

Не используется для:
приема, перевода, увольнения.""",

    "Вход в личный кабинет":
    """1. Приложение 1С
2. Веб:
https://csmedica.1c-cabinet.ru/auth/v2/server/signin?app_req_id=4ebc66c4-c0ef-4267-af99-b4c47da53a62""",

    "Регистрация личного кабинета":
    "Инструкция:\nhttps://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6",

    "Установка мобильного приложения":
    "Инструкция:\nhttps://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6",

    "Настройка уведомления":
    "Инструкция:\nhttps://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6",

    "Подписание документов":
    "Инструкция:\nhttps://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6",

    "Перевыпуск электронной подписи":
    "Инструкция:\nhttps://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6",
}

SMALL_TALK = {"привет", "ок", "спасибо"}

class MessageIn(BaseModel):
    session_id: str
    text: str

def make_response(reply, quick_replies, state):
    return {"reply": reply, "quick_replies": quick_replies, "state": state}

def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "name": "",
            "state": STATE_WAIT_NAME,
            "context": None,
        }
    return sessions[session_id]

def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/api/message")
def api_message(payload: MessageIn):
    session = get_session(payload.session_id)
    text = payload.text.strip()

    if text == "__start__":
        session["state"] = STATE_WAIT_NAME
        return make_response("Привет! Как тебя зовут?", [], STATE_WAIT_NAME)

    if session["state"] == STATE_WAIT_NAME:
        session["name"] = text
        session["state"] = STATE_IDLE
        return make_response(f"{text}, выбери тему 👇", MAIN_MENU, STATE_IDLE)

    if normalize(text) in SMALL_TALK:
        return make_response("Давай посмотрим 👇", MAIN_MENU, STATE_IDLE)

    if text == "Главное меню":
        return make_response("Выбери тему 👇", MAIN_MENU, STATE_IDLE)

    if text in MAIN_MENU:
        session["context"] = text
        return make_response("Выбери вопрос 👇", SUB_MENUS.get(text, []), STATE_IDLE)

    if text in ANSWERS:
        return make_response(ANSWERS[text], MAIN_MENU, STATE_IDLE)

    return make_response("Пока не понял вопрос 🤔 Попробуй выбрать из меню 👇", MAIN_MENU, STATE_IDLE)