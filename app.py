import os
import json
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


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

ADAPTATION_MENU = [
    "План на 1-й день",
    "План на 1-ю неделю",
    "План на 1 месяц",
    "Документы и доступы",
    "Назад",
]

ROLE_MENU = [
    "Кратко о моей должности",
    "Что особенно важно",
    "Ожидания на испытательный срок",
    "Назад",
]

QUESTION_CATEGORIES = [
    "Доступы и системы",
    "Рабочее время и процессы",
    "Рабочие задачи",
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

worksheet = None
sheets_status_message = "Sheets not initialized"


class MessageIn(BaseModel):
    session_id: str
    text: str


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "name": "",
            "department": "",
            "position": "",
            "level": "",
            "start_date": "",
            "probation_end": "",
            "status": "active",
            "adaptation_stage": "",
            "dialog_step": STATE_WAIT_NAME,
            "question_category": "",
            "probation_goals": "",
            "current_tasks": "",
            "last_activity": now_str(),
            "logs": "Сессия создана",
        }
    return sessions[session_id]


def add_log(session: Dict[str, Any], message: str) -> None:
    line = f"[{now_str()}] {message}"
    if session.get("logs"):
        session["logs"] += "\n" + line
    else:
        session["logs"] = line
    session["last_activity"] = now_str()


def init_sheets():
    global worksheet, sheets_status_message

    sheet_id = os.getenv("SHEET_ID", "").strip()
    worksheet_name = os.getenv("WORKSHEET_NAME", "").strip() or "Sheet1"
    creds_json_raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()

    if not sheet_id or not creds_json_raw:
        sheets_status_message = "Sheets: secrets not set -> using memory state."
        print(sheets_status_message)
        return None

    if gspread is None or Credentials is None:
        sheets_status_message = "Sheets: required libraries not installed."
        print(sheets_status_message)
        return None

    try:
        creds_info = json.loads(creds_json_raw)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(credentials)

        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet(worksheet_name)

        sheets_status_message = f"Sheets connected worksheet={worksheet_name}"
        print(sheets_status_message)
        return ws

    except Exception as e:
        sheets_status_message = f"Sheets init error: {e}"
        print(sheets_status_message)
        return None


def ensure_header():
    global worksheet
    if worksheet is None:
        return

    try:
        first_row = worksheet.row_values(1)
        expected = [
            "session_id",
            "Имя",
            "Направление",
            "Должность",
            "Уровень",
            "Дата выхода",
            "Окончание ИС",
            "Статус",
            "Этап адаптации",
            "Шаг диалога",
            "Категория вопроса",
            "Цели ИС",
            "Текущие задачи",
            "Последняя активность",
            "Логи",
        ]

        if first_row != expected:
            worksheet.update("A1:O1", [expected])
            print("Sheets header ensured")
    except Exception as e:
        print(f"Sheets header error: {e}")


def session_to_row(session: Dict[str, Any]):
    return [
        session.get("session_id", ""),
        session.get("name", ""),
        session.get("department", ""),
        session.get("position", ""),
        session.get("level", ""),
        session.get("start_date", ""),
        session.get("probation_end", ""),
        session.get("status", ""),
        session.get("adaptation_stage", ""),
        session.get("dialog_step", ""),
        session.get("question_category", ""),
        session.get("probation_goals", ""),
        session.get("current_tasks", ""),
        session.get("last_activity", ""),
        session.get("logs", ""),
    ]


def save_session_to_sheet(session: Dict[str, Any]) -> None:
    global worksheet
    if worksheet is None:
        return

    try:
        session_id = session["session_id"]
        found = worksheet.find(session_id)
        row_data = session_to_row(session)

        if found:
            row_number = found.row
            worksheet.update(f"A{row_number}:O{row_number}", [row_data])
        else:
            worksheet.append_row(row_data)

    except Exception as e:
        print(f"Sheets save error: {e}")


def adaptation_text(item: str, session: Dict[str, Any]) -> str:
    name = session.get("name", "")
    position = session.get("position", "")
    prefix = "Понял! Вот информация.\n\n"

    if name and position:
        intro = f"{name}, вот ориентир для роли «{position}»:\n\n"
    elif name:
        intro = f"{name}, вот информация:\n\n"
    else:
        intro = ""

    if item == "План на 1-й день":
        return (
            prefix
            + intro
            + "План на 1-й день:\n"
            "1. Познакомиться с командой и руководителем.\n"
            "2. Получить основные доступы и рабочие инструменты.\n"
            "3. Разобраться, к кому обращаться по ключевым вопросам.\n"
            "4. Уточнить первые задачи и ожидания на старт."
        )

    if item == "План на 1-ю неделю":
        return (
            prefix
            + intro
            + "План на 1-ю неделю:\n"
            "1. Понять ключевые рабочие процессы.\n"
            "2. Пройти вводные материалы и обязательные обучения.\n"
            "3. Зафиксировать открытые вопросы по задачам и доступам.\n"
            "4. Свериться с руководителем по приоритетам."
        )

    if item == "План на 1 месяц":
        return (
            prefix
            + intro
            + "План на 1 месяц:\n"
            "1. Освоить основные инструменты и правила работы.\n"
            "2. Войти в регулярный ритм задач.\n"
            "3. Понять ожидания по своей роли.\n"
            "4. Отметить, где еще нужна поддержка или обучение."
        )

    if item == "Документы и доступы":
        return (
            prefix
            + intro
            + "Документы и доступы:\n"
            "1. Корпоративная почта.\n"
            "2. Учетные записи в рабочих системах.\n"
            "3. Доступ к внутренним материалам и регламентам.\n"
            "4. Контакты HR и руководителя.\n"
            "5. Список обязательных документов и сервисов."
        )

    return "Раздел не найден."


def role_text(item: str, session: Dict[str, Any]) -> str:
    name = session.get("name", "")
    position = session.get("position", "").strip() or "вашей должности"

    prefix = "Понял! Вот информация.\n\n"
    hello = f"{name}, " if name else ""

    if item == "Кратко о моей должности":
        return (
            prefix
            + f"{hello}вот краткая выжимка по роли «{position}»:\n\n"
            "Здесь будет краткое описание роли, основных задач и зоны ответственности.\n"
            "На следующем этапе мы подставим сюда персонализированный текст именно под эту должность."
        )

    if item == "Что особенно важно":
        return (
            prefix
            + f"для роли «{position}» важно:\n\n"
            "• понимать свои основные задачи;\n"
            "• знать ключевые процессы и точки взаимодействия;\n"
            "• быстро разобраться в рабочих инструментах;\n"
            "• уточнить ожидания руководителя на стартовом этапе."
        )

    if item == "Ожидания на испытательный срок":
        return (
            prefix
            + f"по роли «{position}» на испытательном сроке обычно важно:\n\n"
            "• освоить базовые процессы;\n"
            "• войти в рабочий ритм;\n"
            "• показать понимание зоны ответственности;\n"
            "• регулярно сверяться по прогрессу с руководителем."
        )

    return "Раздел не найден."


def probation_text(session: Dict[str, Any]) -> str:
    name = session.get("name", "")
    position = session.get("position", "").strip()

    intro = ""
    if name and position:
        intro = f"{name}, вот ориентир для роли «{position}»:\n\n"
    elif name:
        intro = f"{name}, вот ориентир:\n\n"

    return (
        "Понял! Вот информация.\n\n"
        + intro
        + "Испытательный срок:\n"
        "1. Понять ключевые ожидания по своей роли.\n"
        "2. Освоить основные процессы и инструменты.\n"
        "3. Согласовать приоритетные задачи с руководителем.\n"
        "4. Регулярно сверяться по прогрессу."
    )


def get_general_answer(category: str, question: str, session: Dict[str, Any]) -> str:
    name = session.get("name", "")
    hello = f"{name}, " if name else ""

    return (
        f"Спасибо! {hello}я записал твой вопрос.\n\n"
        f"Категория: {category}\n\n"
        f"Текст вопроса:\n{question}\n\n"
        "HR-команда сможет использовать этот лог для ответа и анализа частых запросов."
    )


@app.on_event("startup")
def startup_event():
    global worksheet
    worksheet = init_sheets()
    ensure_header()


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "cs-medica-hr-assistant",
        "message": "API is running"
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "sheets_connected": worksheet is not None,
        "sheets_status": sheets_status_message
    }


@app.post("/api/message")
def api_message(payload: MessageIn):
    session_id = payload.session_id.strip()
    text = payload.text.strip()

    if not session_id:
        return {
            "reply": "Не найден session_id.",
            "quick_replies": [],
            "state": STATE_IDLE,
        }

    session = get_session(session_id)

    if text == "__start__":
        if not session.get("name"):
            session["dialog_step"] = STATE_WAIT_NAME
            add_log(session, "BOT: Старт сценария знакомства")
            save_session_to_sheet(session)
            return {
                "reply": (
                    "Привет!\n\n"
                    "Я Сиэс — HR-ассистент CS Medica.\n\n"
                    "Помогу тебе:\n"
                    "• пройти адаптацию\n"
                    "• разобраться с целями испытательного срока\n"
                    "• найти ответы на рабочие вопросы\n"
                    "• важный момент: давай по возможности общаться в одном браузере, "
                    "чтобы я не забыл наш диалог.\n\n"
                    "Для начала давай познакомимся.\n"
                    "Как я могу к тебе обращаться?"
                ),
                "quick_replies": [],
                "state": STATE_WAIT_NAME,
            }
        else:
            add_log(session, f"BOT: Возврат пользователя {session.get('name', '')}")
            save_session_to_sheet(session)
            return {
                "reply": f"С возвращением, {session.get('name', '')}. Выбери раздел ниже.",
                "quick_replies": MAIN_MENU,
                "state": STATE_IDLE,
            }

    if not text:
        return {
            "reply": "Напиши, пожалуйста, сообщение.",
            "quick_replies": [],
            "state": session.get("dialog_step", STATE_IDLE),
        }

    add_log(session, f"USER: {text}")

    if text == "Назад":
        session["dialog_step"] = STATE_IDLE
        session["question_category"] = ""
        add_log(session, "BOT: Возврат в главное меню")
        save_session_to_sheet(session)
        return {
            "reply": "Понял! Возвращаю в главное меню.",
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if session["dialog_step"] == STATE_WAIT_NAME:
        session["name"] = text
        session["dialog_step"] = STATE_WAIT_DEPARTMENT
        add_log(session, f"Сохранено имя: {text}")
        save_session_to_sheet(session)
        return {
            "reply": f"{text}, приятно познакомиться.\n\nВ каком направлении ты работаешь?",
            "quick_replies": DEPARTMENTS,
            "state": STATE_WAIT_DEPARTMENT,
        }

    if session["dialog_step"] == STATE_WAIT_DEPARTMENT:
        if text not in DEPARTMENTS:
            return {
                "reply": "Пожалуйста, выбери направление кнопкой ниже.",
                "quick_replies": DEPARTMENTS,
                "state": STATE_WAIT_DEPARTMENT,
            }

        session["department"] = text
        session["dialog_step"] = STATE_WAIT_POSITION
        add_log(session, f"Сохранено направление: {text}")
        save_session_to_sheet(session)
        return {
            "reply": "Понял! Теперь напиши, пожалуйста, свою должность.",
            "quick_replies": [],
            "state": STATE_WAIT_POSITION,
        }

    if session["dialog_step"] == STATE_WAIT_POSITION:
        session["position"] = text
        session["dialog_step"] = STATE_IDLE
        add_log(session, f"Сохранена должность: {text}")
        save_session_to_sheet(session)
        return {
            "reply": (
                "Отлично, спасибо.\n\n"
                f"Теперь я смогу подбирать информацию для роли «{text}».\n\n"
                "Выбери раздел ниже."
            ),
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if session["dialog_step"] == STATE_WAIT_QUESTION_CATEGORY:
        if text not in QUESTION_CATEGORIES:
            return {
                "reply": "Пожалуйста, выбери категорию вопроса кнопкой ниже.",
                "quick_replies": QUESTION_CATEGORIES,
                "state": STATE_WAIT_QUESTION_CATEGORY,
            }

        if text == "Назад":
            session["dialog_step"] = STATE_IDLE
            session["question_category"] = ""
            save_session_to_sheet(session)
            return {
                "reply": "Понял! Возвращаю в главное меню.",
                "quick_replies": MAIN_MENU,
                "state": STATE_IDLE,
            }

        session["question_category"] = text
        session["dialog_step"] = STATE_WAIT_QUESTION
        add_log(session, f"Выбрана категория вопроса: {text}")
        save_session_to_sheet(session)
        return {
            "reply": "Понял! Теперь напиши, пожалуйста, сам вопрос.",
            "quick_replies": ["Назад"],
            "state": STATE_WAIT_QUESTION,
        }

    if session["dialog_step"] == STATE_WAIT_QUESTION:
        category = session.get("question_category", "Другое")
        answer = get_general_answer(category, text, session)

        add_log(session, f"Вопрос [{category}]: {text}")
        session["dialog_step"] = STATE_IDLE
        save_session_to_sheet(session)

        return {
            "reply": answer,
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if text == "Адаптация":
        session["dialog_step"] = STATE_IDLE
        add_log(session, "BOT: Открыто меню адаптации")
        save_session_to_sheet(session)
        return {
            "reply": "Понял! Вот информация.\n\nВыбери нужный раздел по адаптации.",
            "quick_replies": ADAPTATION_MENU,
            "state": STATE_IDLE,
        }

    if text in ADAPTATION_MENU:
        if text == "Назад":
            return {
                "reply": "Понял! Возвращаю в главное меню.",
                "quick_replies": MAIN_MENU,
                "state": STATE_IDLE,
            }

        session["adaptation_stage"] = text
        add_log(session, f"Открыт раздел адаптации: {text}")
        save_session_to_sheet(session)
        return {
            "reply": adaptation_text(text, session),
            "quick_replies": ADAPTATION_MENU,
            "state": STATE_IDLE,
        }

    if text == "Испытательный срок":
        session["dialog_step"] = STATE_IDLE
        add_log(session, "BOT: Открыт раздел испытательного срока")
        save_session_to_sheet(session)
        return {
            "reply": probation_text(session),
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if text == "Моя роль":
        session["dialog_step"] = STATE_IDLE
        add_log(session, "BOT: Открыт раздел 'Моя роль'")
        save_session_to_sheet(session)
        return {
            "reply": "Понял! Вот информация.\n\nВыбери нужный раздел по своей роли.",
            "quick_replies": ROLE_MENU,
            "state": STATE_IDLE,
        }

    if text in ROLE_MENU:
        if text == "Назад":
            return {
                "reply": "Понял! Возвращаю в главное меню.",
                "quick_replies": MAIN_MENU,
                "state": STATE_IDLE,
            }

        add_log(session, f"Открыт раздел роли: {text}")
        save_session_to_sheet(session)
        return {
            "reply": role_text(text, session),
            "quick_replies": ROLE_MENU,
            "state": STATE_IDLE,
        }

    if text == "Задать вопрос":
        session["dialog_step"] = STATE_WAIT_QUESTION_CATEGORY
        add_log(session, "BOT: Запрошен выбор категории вопроса")
        save_session_to_sheet(session)
        return {
            "reply": "Понял! Выбери категорию вопроса.",
            "quick_replies": QUESTION_CATEGORIES,
            "state": STATE_WAIT_QUESTION_CATEGORY,
        }

    add_log(session, "BOT: Не распознано, показано главное меню")
    save_session_to_sheet(session)
    return {
        "reply": "Понял! Я пока понимаю основные сценарии. Выбери один из разделов ниже.",
        "quick_replies": MAIN_MENU,
        "state": STATE_IDLE,
    }