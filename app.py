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
    "Цели испытательного срока",
    "Задать вопрос",
]

ADAPTATION_MENU = [
    "План на 1-й день",
    "План на 1-ю неделю",
    "План на 1 месяц",
    "Документы/доступы (чеклист)",
    "Назад",
]

QUESTION_CATEGORIES = [
    "Мои логины и пароли",
    "Организация и оплата рабочего времени",
    "Рабочие процессы и задачи",
    "Другое",
    "Назад",
]

STATE_IDLE = "idle"
STATE_WAIT_NAME = "wait_name"
STATE_WAIT_QUESTION_CATEGORY = "wait_question_category"
STATE_WAIT_QUESTION = "wait_question"

sessions: Dict[str, Dict[str, Any]] = {}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "fio": "",
            "position": "",
            "level": "",
            "start_date": "",
            "probation_end": "",
            "status": "active",
            "adaptation_stage": "",
            "dialog_step": STATE_IDLE,
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


worksheet = None
sheets_status_message = "Sheets not initialized"


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

        sheets_status_message = f"Sheets connected ✅ worksheet={worksheet_name}"
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
            "ФИО",
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
            worksheet.update("A1:N1", [expected])
            print("Sheets header ensured ✅")
    except Exception as e:
        print(f"Sheets header error: {e}")


def session_to_row(session: Dict[str, Any]):
    return [
        session.get("session_id", ""),
        session.get("fio", ""),
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
            worksheet.update(f"A{row_number}:N{row_number}", [row_data])
        else:
            worksheet.append_row(row_data)

    except Exception as e:
        print(f"Sheets save error: {e}")


def adaptation_text(item: str) -> str:
    if item == "План на 1-й день":
        return (
            "План на 1-й день:\n"
            "1. Познакомиться с командой и руководителем.\n"
            "2. Получить базовые доступы.\n"
            "3. Пройти вводные материалы в корпоративном университете.\n"
            "4. Уточнить первые задачи и формат взаимодействия."
        )
    if item == "План на 1-ю неделю":
        return (
            "План на 1-ю неделю:\n"
            "1. Разобраться в ключевых процессах.\n"
            "2. Пройти обязательные вводные курсы.\n"
            "3. Уточнить приоритеты с руководителем.\n"
            "4. Зафиксировать вопросы по работе и доступам."
        )
    if item == "План на 1 месяц":
        return (
            "План на 1 месяц:\n"
            "1. Освоить основные рабочие инструменты.\n"
            "2. Войти в регулярный ритм задач.\n"
            "3. Свериться с ожиданиями на испытательный срок.\n"
            "4. Подготовить список зон, где нужна поддержка."
        )
    if item == "Документы/доступы (чеклист)":
        return (
            "Чек-лист документов и доступов:\n"
            "1. Корпоративная почта.\n"
            "2. Учетные записи в рабочих системах.\n"
            "3. Доступ к корпоративному университету.\n"
            "4. Необходимые внутренние документы и регламенты.\n"
            "5. Контакты HR и руководителя."
        )
    return "Раздел не найден."


def get_general_answer(category: str, question: str) -> str:
    return (
        f"Вопрос записан.\n"
        f"Категория: {category}\n\n"
        f"Текст вопроса:\n{question}\n\n"
        f"Спасибо! HR-команда сможет использовать этот лог для ответа и анализа частых запросов."
    )


class MessageIn(BaseModel):
    session_id: str
    text: str


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
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    session = get_session(session_id)
    add_log(session, f"USER: {text}")

    normalized = text.lower().strip()

    if normalized == "назад":
        session["dialog_step"] = STATE_IDLE
        session["question_category"] = ""
        add_log(session, "BOT: Возврат в главное меню")
        save_session_to_sheet(session)
        return {
            "reply": "Возвращаю в главное меню.",
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if session["dialog_step"] == STATE_WAIT_NAME:
        session["fio"] = text
        session["dialog_step"] = STATE_IDLE
        add_log(session, f"Сохранено ФИО: {text}")
        save_session_to_sheet(session)
        return {
            "reply": f"Спасибо, {text}.\nВыберите нужный раздел по адаптации.",
            "quick_replies": ADAPTATION_MENU,
            "state": STATE_IDLE,
        }

    if session["dialog_step"] == STATE_WAIT_QUESTION_CATEGORY:
        if text not in QUESTION_CATEGORIES:
            return {
                "reply": "Пожалуйста, выберите категорию вопроса кнопкой ниже.",
                "quick_replies": QUESTION_CATEGORIES,
                "state": STATE_WAIT_QUESTION_CATEGORY,
            }

        if text == "Назад":
            session["dialog_step"] = STATE_IDLE
            session["question_category"] = ""
            save_session_to_sheet(session)
            return {
                "reply": "Возвращаю в главное меню.",
                "quick_replies": MAIN_MENU,
                "state": STATE_IDLE,
            }

        session["question_category"] = text
        session["dialog_step"] = STATE_WAIT_QUESTION
        add_log(session, f"Выбрана категория вопроса: {text}")
        save_session_to_sheet(session)
        return {
            "reply": f"Категория выбрана: {text}\nТеперь напишите сам вопрос.",
            "quick_replies": ["Назад"],
            "state": STATE_WAIT_QUESTION,
        }

    if session["dialog_step"] == STATE_WAIT_QUESTION:
        category = session.get("question_category", "Другое")
        answer = get_general_answer(category, text)

        add_log(session, f"Вопрос [{category}]: {text}")
        session["dialog_step"] = STATE_IDLE
        save_session_to_sheet(session)

        return {
            "reply": answer,
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if text == "Адаптация":
        if not session.get("fio"):
            session["dialog_step"] = STATE_WAIT_NAME
            add_log(session, "BOT: Запрошено ФИО перед адаптацией")
            save_session_to_sheet(session)
            return {
                "reply": "Перед началом адаптации напишите, пожалуйста, ваше ФИО.",
                "quick_replies": ["Назад"],
                "state": STATE_WAIT_NAME,
            }
        else:
            session["dialog_step"] = STATE_IDLE
            add_log(session, "BOT: Открыто меню адаптации")
            save_session_to_sheet(session)
            return {
                "reply": f"{session['fio']}, выберите нужный раздел по адаптации.",
                "quick_replies": ADAPTATION_MENU,
                "state": STATE_IDLE,
            }

    if text in ADAPTATION_MENU:
        if text == "Назад":
            session["dialog_step"] = STATE_IDLE
            save_session_to_sheet(session)
            return {
                "reply": "Возвращаю в главное меню.",
                "quick_replies": MAIN_MENU,
                "state": STATE_IDLE,
            }

        session["adaptation_stage"] = text
        add_log(session, f"Открыт раздел адаптации: {text}")
        save_session_to_sheet(session)
        return {
            "reply": adaptation_text(text),
            "quick_replies": ADAPTATION_MENU,
            "state": STATE_IDLE,
        }

    if text == "Цели испытательного срока":
        session["dialog_step"] = STATE_IDLE
        add_log(session, "BOT: Открыт раздел целей испытательного срока")
        save_session_to_sheet(session)
        return {
            "reply": (
                "Цели испытательного срока:\n"
                "1. Понять ключевые ожидания по роли.\n"
                "2. Согласовать приоритетные задачи с руководителем.\n"
                "3. Зафиксировать критерии успешного прохождения адаптации.\n"
                "4. Регулярно сверяться по прогрессу."
            ),
            "quick_replies": MAIN_MENU,
            "state": STATE_IDLE,
        }

    if text == "Задать вопрос":
        session["dialog_step"] = STATE_WAIT_QUESTION_CATEGORY
        add_log(session, "BOT: Запрошен выбор категории вопроса")
        save_session_to_sheet(session)
        return {
            "reply": "Выберите категорию вопроса.",
            "quick_replies": QUESTION_CATEGORIES,
            "state": STATE_WAIT_QUESTION_CATEGORY,
        }

    add_log(session, "BOT: Не распознано, показано главное меню")
    save_session_to_sheet(session)
    return {
        "reply": "Я пока понимаю только основные сценарии. Выберите один из разделов ниже.",
        "quick_replies": MAIN_MENU,
        "state": STATE_IDLE,
    }