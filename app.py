import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="CS Medica HR Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
    "Марктинг",
    "Финансы",
    "HR",
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


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s:\\/@.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_response(reply: str, quick_replies: List[str], state: str) -> Dict[str, Any]:
    return {
        "reply": reply,
        "quick_replies": quick_replies,
        "state": state,
    }


# =========================
# БАЗА ЗНАНИЙ
# =========================

KNOWLEDGE_BASE = [
    {
        "keywords": ["должностная инструкция", "инструкция по должности", "где инструкция", "должностные обязанности", "ДИ"],
        "answer": """Давай разберёмся.

Должностные инструкции находятся на общем диске компании.

Путь:
S:\\Отдел_ДИ

Открой папку своего подразделения и найди файл с нужной должностью.""",
    },
    {
        "keywords": ["корпоративный университет", "где курсы", "обучение"],
        "answer": """Один из этапов адаптации — пройти обучение в корпоративном университете.

Там находятся обязательные курсы:
• Корпоративная жизнь
• Организация рабочего времени

Открой портал корпоративного университета по ссылке:
[вставить ссылку]""",
    },
    {
        "keywords": ["курс корпоративная жизнь"],
        "answer": """Давай посмотрим.

Курс «Корпоративная жизнь» — обязательная часть адаптации.

Он знакомит с:
• культурой компании
• правилами работы
• основными процессами.

Пройти курс можно в корпоративном университете:
[ссылка]""",
    },
    {
        "keywords": ["организация рабочего времени"],
        "answer": """Этот курс помогает разобраться:

• как планировать задачи
• как работать с приоритетами
• как выстраивать рабочий день.

Найти курс можно в корпоративном университете:
[ссылка]""",
    },
    {
        "keywords": ["психологическое тестирование", "мои опросы"],
        "answer": """Психологическое тестирование находится в разделе
«Мои опросы».

Открой раздел и найди соответствующий опрос.

Если он не отображается — напиши HR.""",
    },
    {
        "keywords": ["подпись outlook", "корпоративная подпись", "настройка подписи", "электронная подпись", "корпоративная подпись"],
        "answer": """Для корректной переписки в компании нужно настроить
корпоративную подпись в Outlook.

Инструкция находится здесь:
[ссылка на инструкцию]""",
    },
    {
        "keywords": ["битрикс", "битрикс24", "битрик 24", "Битрикс", "Битрикс 24", "Битрикс24", "Bitrix", "Bitrix24"],
        "answer": """Битрикс24 — основной корпоративный портал.

Через него можно:
• читать новости компании
• искать инструкции
• пользоваться базой знаний.

Открой Битрикс24 по ссылке:
[ссылка]""",
    },
    {
        "keywords": ["база знаний", "инструкции"],
        "answer": """Большинство инструкций находится в Базе знаний
на портале Битрикс24.

Если ты не нашел нужную инструкцию,
можно написать HR

    },
    {
        ""keywords": [
    "1с кабинет сотрудника",
    "личный кабинет 1с",
    "1с личный кабинет",
    "кабинет сотрудника 1с",
    "регистрация в 1с",
    "как зайти в 1с",
    "как скачать 1с кабинет",
    "где 1с кабинет"
        "answer": ""Один из этапов адаптации — зарегистрироваться
в сервисе 1С:Кабинет сотрудника.

После регистрации ты сможешь:
• подписывать документы
• получать уведомления
• управлять кадровыми процессами.

Ссылка для регистрации:
[ссылка]"",
    },
    {
        ""keywords": [
    "приложение 1с",
    "мобильное приложение 1с",
    "скачать 1с",
    "установить 1с",
    "1с на телефон"
        "answer": ""Рекомендуем установить мобильное приложение
1С:Кабинет сотрудника.

Через приложение можно:
• получать уведомления
• подписывать документы
• отслеживать кадровые процессы.""",
    },
    {
        "keywords": ["документы смк", "смк", "СМК", "Система Менеджмента Качества"],
        "answer": """Документы системы менеджмента качества находятся
на общем диске.

Путь:
S:\\03_Документы СМК""",
    },
    {
        "keywords": ["оргполитика"],
        "answer": """Правила работы модуля Оргполитика описаны
в документе «Памятка пользователя».

Найти его можно здесь:

S:\\03_Документы СМК\\Документы СМК по разделам ISO 9001_2015\\Оргполитика""",
    },
    {
        "keywords": ["highper", "КПЭ", "KPI", "мотивация", "премии", "результаты работы"],
        "answer": """Доступ к системе HighPer предоставляется через
руководителя или IT.

Если доступ не работает — напиши в IT-поддержку.""",
    },
    {
        "keywords": ["портрет профессии", " анкета обратной связи", "анкета"],
        "answer": """В рамках адаптации нужно заполнить анкету
«Портрет профессии».

Она помогает лучше понять профессиональный профиль
сотрудника.""",
    },
    {
        "keywords": ["анкета адаптации","анкета портрет профессии", "опрос в конце адаптации", "финальное тестирование"],
        "answer": """После завершения адаптации нужно заполнить
анкету сотрудника по результатам адаптации.

Это помогает улучшать процесс адаптации
для новых сотрудников.""",
    },
    {
        "keywords": ["bestbenefits"],
        "answer": """В компании есть портал корпоративных льгот
BestBenefits.

На нем можно:
• посмотреть предложения партнеров
• получить скидки
• воспользоваться бонусами.

Ссылка:
[ссылка]""",
    },
   {
    "keywords": [
        "контакты hr",
        "hr",
        "кадры",
        "кадровый отдел",
        "как связаться с hr",
        "контакт hr",
        "hr контакт",
        "кому написать hr",
        "hr сергей печенин"
    ],
    "answer": """По вопросам адаптации можно обратиться к HR:

Сергей Печенин
HR-специалист

Напиши ему в мессенджере или через Bitrix24.""",
},
{
    "keywords": [
        "корпоративный университет",
        "КУ",
        "Университет",
        "обучение",
        "курсы",
        "обучение сотрудника",
        "вопрос по обучению",
        "курсы компании"
    ],
    "answer": """По вопросам обучения и корпоративного университета можно обратиться:

Ефремова Надежда
sdo@csmedica.ru""",
},
{
    "keywords": [
        "it поддержка",
        "айти",
        "айтишники",
        "сисадмин",
        "системный администратор",
        "не работает компьютер",
        "экран",
        "монитор",
        "проблема с доступом",
        "не работает система",
        "логин пароль",
        "доступ в систему"
    ],
    "answer": """Если возникли проблемы с доступами или системами,
напиши в IT поддержку:

Звягин Иван или Мансуров Илья
it-help@csmedica.ru""",
},
    {
        "keywords": ["переговорную", "забронировать переговорную", "переговорка", "переговорная комната"],
        "answer": """Переговорные комнаты бронируются
через календарь Outlook.

Инструкция по бронированию:
[ссылка]""",
    },
]

# Нормализуем ключи один раз при запуске
for item in KNOWLEDGE_BASE:
    item["normalized_keywords"] = [normalize(keyword) for keyword in item["keywords"]]


# =========================
# ПОИСК ПО БАЗЕ
# =========================

STOP_WORDS = {
    "как", "где", "что", "это", "у", "в", "на", "по", "и", "или",
    "мне", "мой", "моя", "мое", "с", "к", "для", "а", "но", "ли",
    "же", "про", "под", "из", "от", "до", "не", "ну", "а", "если",
    "нужно", "надо", "можно", "хочу", "хотел", "подскажи", "скажите"
}


def tokenize(text: str) -> List[str]:
    text = normalize(text)
    words = re.findall(r"[a-zа-я0-9]+", text)
    return [w for w in words if len(w) > 1 and w not in STOP_WORDS]


def score_keywords(query_text: str, keywords: List[str]) -> int:
    normalized_query = normalize(query_text)
    query_tokens = set(tokenize(query_text))
    best_score = 0

    for keyword in keywords:
        keyword_norm = normalize(keyword)

        # 1. полное вхождение ключевой фразы
        if keyword_norm in normalized_query:
            best_score = max(best_score, 100)
            continue

        keyword_tokens = set(tokenize(keyword_norm))
        if not keyword_tokens:
            continue

        overlap = len(query_tokens & keyword_tokens)

        # 2. совпали все слова ключа
        if overlap == len(keyword_tokens) and overlap > 0:
            best_score = max(best_score, 60)
            continue

        # 3. совпала значимая часть слов
        if len(keyword_tokens) >= 2 and overlap >= 2:
            best_score = max(best_score, 35)
            continue

        # 4. одно сильное совпадение для коротких ключей
        if len(keyword_tokens) == 1 and overlap == 1:
            best_score = max(best_score, 20)

    return best_score


def search_answer(text: str) -> Optional[str]:
    best_item = None
    best_score = 0

    for item in KNOWLEDGE_BASE:
        score = score_keywords(text, item["keywords"])
        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score >= 20:
        return best_item["answer"]

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

HR_KEYWORDS = [
    "документ",
    "справка",
    "заявление",
    "отпуск",
    "больничн",
    "кадры",
    "оформлен",
    "доступ",
    "логин",
    "пароль",
    "1с",
    "битрикс",
    "outlook",
]

MANAGER_REPLY = "Понял! Тут лучше уточнить у твоего руководителя, это его зона ответственности."
HR_REPLY = "Понял! Тут лучше обратиться к HR."


def detect_fallback(text: str) -> str:
    normalized_text = normalize(text)

    for keyword in MANAGER_KEYWORDS:
        if keyword in normalized_text:
            return MANAGER_REPLY

    for keyword in HR_KEYWORDS:
        if keyword in normalized_text:
            return HR_REPLY

    return HR_REPLY


# =========================
# SESSION
# =========================

def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "name": "",
            "department": "",
            "position": "",
            "dialog_step": STATE_WAIT_NAME,
            "question_category": "",
            "created_at": now_str(),
            "updated_at": now_str(),
        }
    return sessions[session_id]


def reset_session(session: Dict[str, Any]) -> None:
    session["name"] = ""
    session["department"] = ""
    session["position"] = ""
    session["dialog_step"] = STATE_WAIT_NAME
    session["question_category"] = ""
    session["updated_at"] = now_str()


# =========================
# ОБРАБОТКА МЕНЮ
# =========================

def handle_main_menu(text: str) -> Optional[Dict[str, Any]]:
    normalized_text = normalize(text)

    if normalized_text == normalize("Адаптация"):
        return make_response(
            """Давай посмотрим.

В адаптацию обычно входят:
• должностная инструкция
• обязательные курсы
• психологическое тестирование
• настройка рабочих систем
• знакомство с внутренними сервисами

Можешь выбрать следующий вопрос или просто написать его текстом.""",
            MAIN_MENU,
            STATE_IDLE,
        )

    if normalized_text == normalize("Испытательный срок"):
        return make_response(
            """Давай разберёмся.

По вопросам испытательного срока лучше ориентироваться на:
• задачи на период адаптации
• ожидания руководителя
• промежуточную обратную связь
• финальные результаты периода

Если вопрос про цели, результаты или приоритеты — лучше уточнить у руководителя.""",
            MAIN_MENU,
            STATE_IDLE,
        )

    if normalized_text == normalize("Моя роль"):
        return make_response(
            """По вопросам роли, задач, приоритетов и ожидаемых результатов лучше сверяться с руководителем.

Если хочешь, можешь написать свой вопрос текстом — я подскажу, куда лучше обратиться.""",
            MAIN_MENU,
            STATE_IDLE,
        )

    if normalized_text == normalize("Задать вопрос"):
        return make_response(
            "Напиши вопрос своими словами, а я постараюсь помочь.",
            [],
            STATE_IDLE,
        )

    return None


# =========================
# API
# =========================

@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/message")
def api_message(payload: MessageIn) -> Dict[str, Any]:
    session_id = payload.session_id.strip()
    text = payload.text.strip()
    session = get_session(session_id)
    session["updated_at"] = now_str()

    if not text:
        return make_response(
            "Напиши, пожалуйста, сообщение, и я постараюсь помочь.",
            MAIN_MENU if session["dialog_step"] == STATE_IDLE else [],
            session["dialog_step"],
        )

    if text == "__start__":
        reset_session(session)
        return make_response(
            """Привет!

Я СиЭс — HR-ассистент компании CS Medica.

Я могу помочь:
• пройти адаптацию
• найти инструкции
• разобраться с курсами
• подсказать, к кому обратиться

Для начала давай познакомимся.

Как я могу к тебе обращаться?""",
            [],
            STATE_WAIT_NAME,
        )

    # =========================
    # СЦЕНАРИЙ ЗНАКОМСТВА
    # =========================

    if session["dialog_step"] == STATE_WAIT_NAME:
        session["name"] = text
        session["dialog_step"] = STATE_WAIT_DEPARTMENT
        return make_response(
            f"{text}, приятно познакомиться.\n\nВ каком направлении ты работаешь?",
            DEPARTMENTS,
            STATE_WAIT_DEPARTMENT,
        )

    if session["dialog_step"] == STATE_WAIT_DEPARTMENT:
        session["department"] = text
        session["dialog_step"] = STATE_WAIT_POSITION
        return make_response(
            "Понял! Теперь напиши, пожалуйста, свою должность.",
            [],
            STATE_WAIT_POSITION,
        )

    if session["dialog_step"] == STATE_WAIT_POSITION:
        session["position"] = text
        session["dialog_step"] = STATE_IDLE
        return make_response(
            """Отлично!

Теперь я смогу помогать тебе с адаптацией.

Выбери раздел ниже или задай вопрос.""",
            MAIN_MENU,
            STATE_IDLE,
        )

    # =========================
    # ГЛАВНОЕ МЕНЮ
    # =========================

    menu_response = handle_main_menu(text)
    if menu_response:
        return menu_response

    # =========================
    # ПОИСК В БАЗЕ ЗНАНИЙ
    # =========================

    answer = search_answer(text)
    if answer:
        return make_response(answer, MAIN_MENU, STATE_IDLE)

    # =========================
    # FALLBACK
    # =========================

    return make_response(detect_fallback(text), MAIN_MENU, STATE_IDLE)