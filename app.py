import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="CS Medica HR Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAIN_MENU = [
    "Адаптация",
    "Испытательный срок",
    "Моя роль",
    "Задать вопрос",
]

DEPARTMENTS = [
    "Продажи",
    "Офис",
    "Логистика",
    "IT",
    "Другое",
]

QUESTION_CATEGORIES = [
    "Рабочие задачи",
    "Оформление и документы",
    "Доступы и системы",
    "Другое",
    "Назад",
]

STATE_WAIT_NAME = "wait_name"
STATE_WAIT_DEPARTMENT = "wait_department"
STATE_WAIT_POSITION = "wait_position"
STATE_IDLE = "idle"
STATE_WAIT_QUESTION_CATEGORY = "wait_question_category"
STATE_WAIT_QUESTION = "wait_question"

sessions: Dict[str, Dict[str, Any]] = {}

class MessageIn(BaseModel):
    session_id: str
    text: str


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize(text: str):
    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================
# БАЗА ЗНАНИЙ
# =========================

KNOWLEDGE_BASE = [

{
"keywords": ["должностная инструкция", "инструкция по должности", "где инструкция"],
"answer":
"""Давай разберёмся.

Должностные инструкции находятся на общем диске компании.

Путь:
S:\\Отдел_ДИ

Открой папку своего подразделения и найди файл с нужной должностью."""
},

{
"keywords": ["корпоративный университет", "где курсы", "обучение"],
"answer":
"""Один из этапов адаптации — пройти обучение в корпоративном университете.

Там находятся обязательные курсы:
• Корпоративная жизнь
• Организация рабочего времени

Открой портал корпоративного университета по ссылке:
[вставить ссылку]"""
},

{
"keywords": ["курс корпоративная жизнь"],
"answer":
"""Давай посмотрим.

Курс «Корпоративная жизнь» — обязательная часть адаптации.

Он знакомит с:
• культурой компании
• правилами работы
• основными процессами.

Пройти курс можно в корпоративном университете:
[ссылка]"""
},

{
"keywords": ["организация рабочего времени"],
"answer":
"""Этот курс помогает разобраться:

• как планировать задачи
• как работать с приоритетами
• как выстраивать рабочий день.

Найти курс можно в корпоративном университете:
[ссылка]"""
},

{
"keywords": ["психологическое тестирование", "мои опросы"],
"answer":
"""Психологическое тестирование находится в разделе
«Мои опросы».

Открой раздел и найди соответствующий опрос.

Если он не отображается — напиши HR."""
},

{
"keywords": ["подпись outlook", "корпоративная подпись"],
"answer":
"""Для корректной переписки в компании нужно настроить
корпоративную подпись в Outlook.

Инструкция находится здесь:
[ссылка на инструкцию]"""
},

{
"keywords": ["битрикс", "битрикс24"],
"answer":
"""Битрикс24 — основной корпоративный портал.

Через него можно:
• читать новости компании
• искать инструкции
• пользоваться базой знаний.

Открой Битрикс24 по ссылке:
[ссылка]"""
},

{
"keywords": ["база знаний", "инструкции"],
"answer":
"""Большинство инструкций находится в Базе знаний
на портале Битрикс24.

Если ты не нашел нужную инструкцию,
можно написать на почту:

it-help@csmedica.ru"""
},

{
"keywords": ["1с кабинет сотрудника", "личный кабинет 1с"],
"answer":
"""Один из этапов адаптации — зарегистрироваться
в сервисе 1С:Кабинет сотрудника.

После регистрации ты сможешь:
• подписывать документы
• получать уведомления
• управлять кадровыми процессами.

Ссылка для регистрации:
[ссылка]"""
},

{
"keywords": ["приложение 1с"],
"answer":
"""Рекомендуем установить мобильное приложение
1С:Кабинет сотрудника.

Через приложение можно:
• получать уведомления
• подписывать документы
• отслеживать кадровые процессы."""
},

{
"keywords": ["документы смк", "смк"],
"answer":
"""Документы системы менеджмента качества находятся
на общем диске.

Путь:
S:\\03_Документы СМК"""
},

{
"keywords": ["оргполитика"],
"answer":
"""Правила работы модуля Оргполитика описаны
в документе «Памятка пользователя».

Найти его можно здесь:

S:\\03_Документы СМК\\Документы СМК по разделам ISO 9001_2015\\Оргполитика"""
},

{
"keywords": ["highper"],
"answer":
"""Доступ к системе HighPer предоставляется через
руководителя или IT.

Если доступ не работает — напиши в IT-поддержку."""
},

{
"keywords": ["портрет профессии"],
"answer":
"""В рамках адаптации нужно заполнить анкету
«Портрет профессии».

Она помогает лучше понять профессиональный профиль
сотрудника."""
},

{
"keywords": ["анкета адаптации"],
"answer":
"""После завершения адаптации нужно заполнить
анкету сотрудника по результатам адаптации.

Это помогает улучшать процесс адаптации
для новых сотрудников."""
},

{
"keywords": ["bestbenefits"],
"answer":
"""В компании есть портал корпоративных льгот
BestBenefits.

На нем можно:
• посмотреть предложения партнеров
• получить скидки
• воспользоваться бонусами.

Ссылка:
[ссылка]"""
},

{
"keywords": ["контакты", "к кому обратиться"],
"answer":
"""Если возник вопрос, можно обратиться:

По обучению:
Ефремова Надежда
sdo@csmedica.ru

По адаптации:
непосредственный руководитель
или HR Сергей Печенин."""
},

{
"keywords": ["переговорную", "забронировать переговорную"],
"answer":
"""Переговорные комнаты бронируются
через календарь Outlook.

Инструкция по бронированию:
[ссылка]"""
}

]


# =========================
# ПОИСК ПО БАЗЕ
# =========================

def search_answer(text: str) -> Optional[str]:

text = normalize(text)

for item in KNOWLEDGE_BASE:

for keyword in item["keywords"]:

if keyword in text:

return item["answer"]

return None


# =========================
# FALLBACK
# =========================

MANAGER_KEYWORDS = [
"задач",
"приоритет",
"ответствен",
"kpi",
"результат",
"что мне делать",
"рабочая задача",
]

MANAGER_REPLY = "Понял! Тут лучше уточнить у твоего руководителя, это его зона ответственности."

HR_REPLY = "Понял! Тут лучше обратиться к HR."


# =========================
# SESSION
# =========================

def get_session(session_id: str):

if session_id not in sessions:

sessions[session_id] = {
"session_id": session_id,
"name": "",
"department": "",
"position": "",
"dialog_step": STATE_WAIT_NAME,
"question_category": ""
}

return sessions[session_id]


# =========================
# API
# =========================

@app.post("/api/message")
def api_message(payload: MessageIn):

session_id = payload.session_id
text = payload.text.strip()

session = get_session(session_id)

if text == "__start__":

return {
"reply":
"""Привет!

Я Сиэс — HR-ассистент компании CS Medica.

Я могу помочь:
• пройти адаптацию
• найти инструкции
• разобраться с курсами
• подсказать к кому обратиться.

Для начала давай познакомимся.

Как я могу к тебе обращаться?""",
"quick_replies": [],
"state": STATE_WAIT_NAME
}

# =========================
# СЦЕНАРИЙ ЗНАКОМСТВА
# =========================

if session["dialog_step"] == STATE_WAIT_NAME:

session["name"] = text
session["dialog_step"] = STATE_WAIT_DEPARTMENT

return {
"reply": f"{text}, приятно познакомиться.\n\nВ каком направлении ты работаешь?",
"quick_replies": DEPARTMENTS,
"state": STATE_WAIT_DEPARTMENT
}

if session["dialog_step"] == STATE_WAIT_DEPARTMENT:

session["department"] = text
session["dialog_step"] = STATE_WAIT_POSITION

return {
"reply": "Понял! Теперь напиши, пожалуйста, свою должность.",
"quick_replies": [],
"state": STATE_WAIT_POSITION
}

if session["dialog_step"] == STATE_WAIT_POSITION:

session["position"] = text
session["dialog_step"] = STATE_IDLE

return {
"reply":
"""Отлично!

Теперь я смогу помогать тебе с адаптацией.

Выбери раздел ниже или задай вопрос.""",
"quick_replies": MAIN_MENU,
"state": STATE_IDLE
}

# =========================
# ПОИСК В БАЗЕ ЗНАНИЙ
# =========================

answer = search_answer(text)

if answer:

return {
"reply": answer,
"quick_replies": MAIN_MENU,
"state": STATE_IDLE
}

# =========================
# FALLBACK
# =========================

for k in MANAGER_KEYWORDS:

if k in normalize(text):

return {
"reply": MANAGER_REPLY,
"quick_replies": MAIN_MENU,
"state": STATE_IDLE
}

return {
"reply": HR_REPLY,
"quick_replies": MAIN_MENU,
"state": STATE_IDLE
}