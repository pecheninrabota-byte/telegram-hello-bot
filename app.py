import re
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
STATE_FREE_INPUT = "free_input"  # режим свободного ввода

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

    # --- МАГАЗИН ---
    "Как найти магазин бонусов":
    """Магазин бонусов расположен на главной страниц Битрикс24 в правом меню. 
Вот тебе ссылка для улобного перехода:
https://bitrix.csdeskwork.ru/bonus/shop/""",

    "Как списать бонусы?":
    """Бонусы можно списать в магазине бонусов. Ты выбираешь нужную тебе позицию, нажимаешь на кнопку "получить". После этого в битриксе прийдет собщение с подтверждением покупки от Вольф Марии. 
Все кроме сертификатов ozon работает так: ты покупаешь вещь за свеой счет, а 10 числа в зарплату списанная сумма начислится плюсом.""",

    "Как накопить бонусы?":
    """Бонусы можно накопить разными путями:
Спорт — участие в забегах и проекте «Шаги»
Наставничество — обучение новичков
Приведи друга — баллы за трудоустройство кандидата
Праздники — дни рождения, 23 февраля, 8 Марта
Юбилеи — каждые 5 лет работы""",

    "Как купить сертификат?":
    """Сертификат Ozon можно купить в магазине бонусов в любой день, но придет он ближайшего 15 или 30 числа.
Ссылка на магазин бонусов в Битрикс24:
https://bitrix.csdeskwork.ru/bonus/shop/""",

    # --- ДМС ---
    "Где найти номер полиса?":
    """Номер твоего полиса находтся в личном кабинете приложения ИНГОССТРАХ. Скачать его можно в твоем магазине приложенийили на официальном сайте компании по ссылке:
https://www.ingos.ru/

Для твоего удоства я собрал статью со всеми популярными вопросами по ДМС внутри нашей компании по ссылке:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "План ДМС":
    """План ДМС можно найти в личном кабинете приложения ИНГОССТРАХ. Скачать его можно в твоем магазине приложенийили на официальном сайте компании по ссылке:
https://www.ingos.ru/

Для твоего удоства я собрал статью со всеми популярными вопросами по ДМС внутри нашей компании по ссылке:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "Как согласовать анализы?":
    """Анализы согласует врач по гарантийному письму после приема. Оповещение придет в в личном кабинете приложения ИНГОССТРАХ. Скачать его можно в твоем магазине приложенийили на официальном сайте компании по ссылке:
https://www.ingos.ru/

Для твоего удоства я собрал статью со всеми популярными вопросами по ДМС внутри нашей компании по ссылке:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "Как найти или выбрать врача?":
    """Найти или выбрать врача можно в личном кабинете приложения ИНГОССТРАХ. Скачать его можно в твоем магазине приложенийили на официальном сайте компании по ссылке:
https://www.ingos.ru/

Для твоего удоства я собрал статью со всеми популярными вопросами по ДМС внутри нашей компании по ссылке:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    "Где найти список клиник":
    """Список клиник приходит отдельным файлом на почту при продлении полиса для старых сотрудников и при подключении новых.
Для твоего удоства я собрал статью со всеми популярными вопросами по ДМС внутри нашей компании по ссылке:
https://csmedica-1.ispring.ru/app/preview/c8edf521-f2af-11f0-a291-6e04853a1ce6""",

    # --- ОТГУЛЫ ---
    "Сколько у меня осталось отгулов?":
    """Посмотреть остаток своих отгулов можно в реестре отгулов в Битрикс24, он расположен в левом боковм меню. Либо можешь просто перейти туда по ссылке:
https://bitrix.csdeskwork.ru/page/reestr_otgulov/spisok/type/1056/list/category/14/""",

    "Когда отгулы сгорят?":
    """Даты окончания действия своих отгулов можно увидеть в реестре отгулов в Битрикс24, он расположен в левом боковм меню. Либо можешь просто перейти туда по ссылке:
https://bitrix.csdeskwork.ru/page/reestr_otgulov/spisok/type/1056/list/category/14/""",

    # --- КУ ---
    "КУ: вход в личный кабинет":
    """Логин и пароль для входа тебе приходили в первый рабочий день на почту. А в сам КУ можно попасть через главную страницу Битрикс24 или по ссылке:
https://bitrix.csdeskwork.ru/knowledge/otgul/""",

    "КУ: забыли пароль":
    """Пароль можно восстановить через кнопку "забыли пароль".""",

    "Оформить заявку на обучение":
    """Для оформлени заяки на обучение нужно написать в битрикс Ефремовой Надежде.""",

    # --- HIGHPER ---
    "Что такое HighPer?":
    """Это программа для автоматизации управлением KPI. Попасть туда можно в левом боковом меню Битрикс 24 или по ссылке:
https://csmedica.highper.ru/Account/Login?ReturnUrl=%2f

Еще я подготовил небольшую статью про эту программу с ответами на все популярные вопросы: https://csmedica-1.ispring.ru/app/preview/f4d03c14-570e-11f0-8bea-366ce65cb574""",

    "HighPer: вход в личный кабинет":
    """В личный кабинет можно войти по лгину и паролю, которые приходили тебе на электронную почту после прохождения испытательного срока. Попасть туда можно в левом боковом меню Битрикс 24 или по ссылке:
https://csmedica.highper.ru/Account/Login?ReturnUrl=%2f

Еще я подготовил небольшую статью про эту программу с ответами на все популярные вопросы: https://csmedica-1.ispring.ru/app/preview/f4d03c14-570e-11f0-8bea-366ce65cb574""",

    "HighPer: забыли пароль":
    """Если ты забыл пароль, ты можешь его поменять через кнопку "я забыл пароль".""",

    # --- 1С ---
    "Что такое 1С личный кабинет сотрудника?":
    """1С личный кабинет сотрудника это кадровый электронный документооборот (КЭДО) для работы с такими документами, как приказы на премии, расчетные листки, командировки, приказы на отпуск.
В КЭДО не подписываются приказы на прием, перевод и увольнение.""",

    "Вход в личный кабинет":
    """В личный кабинет можно попасть двумя способами:
1. Скачать приложение "1С личный кабинет сотрудника"
2. Использовать веб версию:
https://csmedica.1c-cabinet.ru/auth/v2/server/signin?app_req_id=4ebc66c4-c0ef-4267-af99-b4c47da53a62""",

    "Регистрация личного кабинета":
    """Подробный ответ на этот вопрос находится в лонгриде по ссылке:
    https://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6""",

    "Установка мобильного приложения":
    """Подробный ответ на этот вопрос находится в лонгриде по ссылке:
    https://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6""",

    "Настройка уведомления":
    """Подробный ответ на этот вопрос находится в лонгриде по ссылке:
    https://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6""",

    "Подписание документов":
    """Подробный ответ на этот вопрос находится в лонгриде по ссылке:
    https://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6""",

    "Перевыпуск электронной подписи":
    """Подробный ответ на этот вопрос находится в лонгриде по ссылке:
    https://csmedica-1.ispring.ru/app/preview/0db4012c-275c-11f1-a4da-42fe26cdc3d6""",
}

SMALL_TALK = {"привет", "ок", "спасибо"}

# Ключевые слова для поиска ответа по разделам
KEYWORDS = {
    "ДМС": ["полис", "дмс", "анализы", "врач", "клиника", "лечение", "больница", "ингосстрах"],
    "Магазин подарков": ["бонус", "магазин", "подарок", "сертификат", "озон", "списать", "накопить"],
    "Отгулы": ["отгул", "остаток", "сгорел", "сгорят", "выйти"],
    "Корпоративный университет": ["ку", "обучение", "курс", "университет", "знания"],
    "HighPer": ["highper", "kpi", "показатель", "эффективность"],
    "1С личный кабинет": ["1с", "кадры", "документ", "подпись", "приказ", "кабинет"]
}

# Контакты специалистов
CONTACTS = {
    "ДМС": "по ДМС можно обратиться к Светлане Климовой",
    "Магазин подарков": "по бонусной программе — к Марии Вольф",
    "Отгулы": "по отгулам — к руководителю или в отдел кадров",
    "Корпоративный университет": "по обучению — к Ефремовой Надежде",
    "HighPer": "по HighPer — к руководителю или в отдел методологии",
    "1С личный кабинет": "по 1С — в службу поддержки или к кадровикам",
    "default": "напиши в отдел кадров или своему руководителю"
}


class MessageIn(BaseModel):
    session_id: str | None = None
    text: str | None = None
    message: str | None = None


def make_response(reply, quick_replies, state):
    return {"reply": reply, "quick_replies": quick_replies, "state": state}


def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "name": "",
            "state": STATE_WAIT_NAME,
            "current_section": None,
        }
    return sessions[session_id]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def find_answer_by_keywords(question: str):
    """Ищет подходящий ответ по ключевым словам в вопросах из ANSWERS"""
    question_lower = question.lower()
    
    # Прямое совпадение
    for q in ANSWERS:
        if q.lower() in question_lower or question_lower in q.lower():
            return ANSWERS[q], None
    
    # Поиск по ключевым словам раздела
    for section, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in question_lower:
                # Нашли раздел, возвращаем контакт специалиста
                return None, CONTACTS.get(section, CONTACTS["default"])
    
    return None, CONTACTS["default"]


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/api/message")
def api_message(payload: MessageIn):
    text = (payload.text or payload.message or "").strip()
    session_id = payload.session_id or "default"
    session = get_session(session_id)

    if text == "__start__":
        session["state"] = STATE_WAIT_NAME
        session["current_section"] = None
        return make_response(
            "Привет! Я СиЭс — HR-ассистент 👋\n\n"
            "Помогу тебе найти ответы по внутренним вопросам: ДМС, отгулы, обучение и другое.\n\n"
            "Давай начнем — как тебя зовут?",
            [],
            STATE_WAIT_NAME
        )

    if session["state"] == STATE_WAIT_NAME:
        session["name"] = text
        session["state"] = STATE_IDLE
        session["current_section"] = None
        return make_response(f"{text}, выбери тему 👇", MAIN_MENU, STATE_IDLE)

    if normalize(text) in SMALL_TALK:
        return make_response("Давай посмотрим 👇", MAIN_MENU, STATE_IDLE)

    # Обработка кнопки "Главное меню"
    if text == "Главное меню":
        session["current_section"] = None
        session["state"] = STATE_IDLE
        return make_response("Выбери тему 👇", MAIN_MENU, STATE_IDLE)

    # Если выбрана тема из главного меню
    if text in MAIN_MENU:
        # Если выбрана кнопка "Не нашёл ответ" — переходим в режим свободного ввода
        if text == "Не нашёл ответ":
            session["state"] = STATE_FREE_INPUT
            return make_response(
                "Напиши свой вопрос текстом, я поищу ответ или подскажу, к кому обратиться 👇\n\n"
                "Можешь написать: как накопить бонусы, что такое HighPer, где найти номер полиса и т.д.",
                [],
                STATE_FREE_INPUT
            )
        
        session["current_section"] = text
        session["state"] = STATE_IDLE
        return make_response("Выбери вопрос 👇", SUB_MENUS.get(text, []), STATE_IDLE)

    # Режим свободного ввода
    if session["state"] == STATE_FREE_INPUT:
        answer, contact = find_answer_by_keywords(text)
        
        if answer:
            # Нашли готовый ответ — показываем его и возвращаем в текущий раздел
            if session["current_section"]:
                section_menu = SUB_MENUS.get(session["current_section"], MAIN_MENU)
                session["state"] = STATE_IDLE
                return make_response(answer, section_menu, STATE_IDLE)
            else:
                session["state"] = STATE_IDLE
                return make_response(answer, MAIN_MENU, STATE_IDLE)
        else:
            # Не нашли ответ — даем контакт специалиста и возвращаем в меню
            session["state"] = STATE_IDLE
            reply = f"Не смог найти точный ответ на твой вопрос 😔\n\nНо я знаю, кто поможет: {contact}\n\nВыбери тему из меню 👇"
            if session["current_section"]:
                section_menu = SUB_MENUS.get(session["current_section"], MAIN_MENU)
                return make_response(reply, section_menu, STATE_IDLE)
            return make_response(reply, MAIN_MENU, STATE_IDLE)

    # Если вопрос из ANSWERS в обычном режиме
    if text in ANSWERS:
        if session["current_section"]:
            section_menu = SUB_MENUS.get(session["current_section"], MAIN_MENU)
            return make_response(ANSWERS[text], section_menu, STATE_IDLE)
        return make_response(ANSWERS[text], MAIN_MENU, STATE_IDLE)

    return make_response("Пока не понял вопрос 🤔 Попробуй выбрать из меню 👇", MAIN_MENU, STATE_IDLE)