import re
import random
import gspread
from datetime import datetime
from typing import Dict, Any
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

STATE_WAIT_NAME = "wait_name"
STATE_IDLE = "idle"

GOOGLE_SHEETS_WEBHOOK = "https://script.google.com/macros/s/AKfycbxi2sXker_ofkg_DyQvwnIrNJuFcsCnB_qHlBwUwBJ9GFA59fhELEsdZag18Sb6kEzsEg/exec"
GOOGLE_SHEETS_NAME = "HR Bot Analytics"
GOOGLE_SHEETS_KB_WORKSHEET = "Обучение бота"
GOOGLE_CREDENTIALS_FILE = "credentials.json"

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
        "Как войти в личный кабинет?",
        "Что делать, если забыли пароль",
        "Оформить заявку на обучение",
        "Не нашёл ответ",
        "Главное меню"
    ],
    "HighPer": [
        "Что такое HighPer?",
        "Как войти в личный кабинет?",
        "Что делать, если забыли пароль",
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

    # --- МАГАЗИН БОНУСОВ ---
    "Как найти магазин бонусов":
    """Магазин бонусов расположен на главной странице Битрикс24 в правом меню.
Вот ссылка для удобного перехода:
https://bitrix.csdeskwork.ru/bonus/shop/""",

    "Как списать бонусы?":
    """Бонусы можно списать в магазине бонусов.

Ты выбираешь нужную тебе позицию и нажимаешь "получить".
После этого в Битрикс придет сообщение с подтверждением покупки от Вольф Марии.

Все кроме сертификатов Ozon работает так:
ты покупаешь вещь за свой счет, а 10 числа в зарплату сумма вернется плюсом.""",

    "Как накопить бонусы?":
    """Бонусы можно накопить разными путями:

Спорт — участие в забегах и проекте «Шаги»
Наставничество — обучение новичков
Приведи друга — баллы за трудоустройство кандидата
Праздники — дни рождения, 23 февраля, 8 Марта
Юбилеи — каждые 5 лет работы""",

    "Как купить сертификат?":
    """Сертификат Ozon можно купить в магазине бонусов в любой день,
но придет он ближайшего 15 или 30 числа.

Ссылка:
https://bitrix.csdeskwork.ru/bonus/shop/""",

    # --- ДМС ---
    "Где найти номер полиса?":
    """Номер полиса находится в приложении ИНГОССТРАХ.

Скачать можно здесь:
https://www.ingos.ru/

Также я собрал статью со всеми вопросами по ДМС:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "План ДМС":
    """План ДМС находится в приложении ИНГОССТРАХ.

Скачать:
https://www.ingos.ru/

Подробная статья:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "Как согласовать анализы?":
    """Анализы согласует врач после приема по гарантийному письму.

Оповещение придет в приложении ИНГОССТРАХ:
https://www.ingos.ru/

Подробная статья:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "Как найти или выбрать врача?":
    """Найти врача можно в приложении ИНГОССТРАХ:
https://www.ingos.ru/

Подробная статья:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "Где найти список клиник":
    """Список клиник приходит на почту при подключении или продлении полиса.

Подробная статья:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    # --- ОТГУЛЫ ---
    "Сколько у меня осталось отгулов?":
    """Посмотреть остаток можно в реестре отгулов в Битрикс24:
https://bitrix.csdeskwork.ru/page/reestr_otgulov/spisok/type/1056/list/category/14/""",

    "Когда отгулы сгорят?":
    """Даты окончания отгулов можно увидеть в реестре:
https://bitrix.csdeskwork.ru/page/reestr_otgulov/spisok/type/1056/list/category/14/""",

    # --- КУ ---
    "Как войти в личный кабинет?":
    """Логин и пароль приходили в первый рабочий день на почту.

Перейти можно через Битрикс24 или по ссылке:
https://bitrix.csdeskwork.ru/knowledge/otgul/""",

    "Что делать, если забыли пароль":
    """Используй кнопку "забыли пароль" на странице входа.""",

    "Оформить заявку на обучение":
    """Напиши в Битрикс Ефремовой Надежде.""",

    # --- HIGHPER ---
    "Что такое HighPer?":
    """Это система управления KPI.

Вход:
https://csmedica.highper.ru/Account/Login?ReturnUrl=%2f

Статья:
https://csmedica-1.ispring.ru/app/preview/f4d03c14-570e-11f0-8bea-366ce65cb574""",

    # --- 1С ---
    "Что такое 1С личный кабинет сотрудника?":
    """Это система КЭДО для работы с кадровыми документами.

Не используется для:
приема, перевода и увольнения.""",

    "Вход в личный кабинет":
    """Можно войти:

1. Через приложение "1С личный кабинет сотрудника"
2. Через веб:
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