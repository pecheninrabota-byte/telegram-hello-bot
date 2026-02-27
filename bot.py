import os
import json
from datetime import datetime

import telebot
from telebot import types

import gspread
from google.oauth2.service_account import Credentials


# ----------------------------
# Telegram
# ----------------------------
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN not set")

bot = telebot.TeleBot(TOKEN)


# ----------------------------
# Google Sheets
# ----------------------------
SHEET_ID = os.environ.get("SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
WORKSHEET_NAME = os.environ.get("WORKSHEET_NAME")  # желательно: "Сотрудники"

ws = None  # worksheet


def init_sheets():
    global ws

    if not SHEET_ID or not GOOGLE_CREDENTIALS_JSON:
        print("Sheets: secrets not set.")
        ws = None
        return

    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    except Exception as e:
        print("Invalid GOOGLE_CREDENTIALS_JSON:", e)
        ws = None
        return

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SHEET_ID)

    if WORKSHEET_NAME:
        ws = sh.worksheet(WORKSHEET_NAME)
    else:
        ws = sh.get_worksheet(0)

    print(f"Sheets connected ✅ ({ws.title})")


def _ensure_ws():
    return ws is not None


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------
# Columns (новая структура)
# A telegram_id
# B ФИО
# C Должность
# D Уровень
# E Дата выхода
# F Окончание ИС
# G Статус
# H Этап адаптации
# I Шаг диалога
# J Категория вопроса
# K Цели ИС
# L Текущие задачи
# M Последняя активность
# N Логи
# ----------------------------
COL_TELEGRAM_ID = 1
COL_FIO = 2
COL_POSITION = 3
COL_LEVEL = 4
COL_START_DATE = 5
COL_END_DATE = 6
COL_STATUS = 7
COL_STAGE = 8
COL_DIALOG_STEP = 9
COL_QUESTION_CAT = 10
COL_GOALS = 11
COL_TASKS = 12
COL_LAST_ACTIVE = 13
COL_LOGS = 14


def _touch_last_active(chat_id: int):
    if not _ensure_ws():
        return
    row = get_or_create_user_row(chat_id)
    if not row:
        return
    ws.update_cell(row, COL_LAST_ACTIVE, _now_str())


def get_or_create_user_row(chat_id: int) -> int:
    """Находит строку пользователя по telegram_id (A). Если нет — создаёт."""
    if not _ensure_ws():
        return 0

    tid = str(chat_id)
    try:
        cell = ws.find(tid, in_column=COL_TELEGRAM_ID)
        return cell.row
    except Exception:
        # Создаём новую строку A..N
        # telegram_id в A, статус "Новый", step idle, остальное пустое
        ws.append_row(
            [
                tid,            # A telegram_id
                "",             # B ФИО
                "",             # C Должность
                "",             # D Уровень
                "",             # E Дата выхода
                "",             # F Окончание ИС
                "Новый",        # G Статус
                "",             # H Этап адаптации
                "idle",         # I Шаг диалога
                "",             # J Категория вопроса
                "",             # K Цели ИС
                "",             # L Текущие задачи
                _now_str(),     # M Последняя активность
                "",             # N Логи
            ],
            value_input_option="USER_ENTERED",
        )
        cell = ws.find(tid, in_column=COL_TELEGRAM_ID)
        return cell.row


def append_log(chat_id: int, event: str, payload: dict | None = None):
    """Добавляет строку лога в колонку N (Логи) в строке пользователя."""
    if not _ensure_ws():
        return

    row = get_or_create_user_row(chat_id)
    if not row:
        return

    _touch_last_active(chat_id)

    current = ws.cell(row, COL_LOGS).value or ""

    payload_str = ""
    if payload:
        try:
            payload_str = " | " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            payload_str = ""

    line = f"[{_now_str()}] {event}{payload_str}"

    if current.strip():
        new_val = current.rstrip() + "\n" + line
    else:
        new_val = line

    if len(new_val) > 45000:
        new_val = new_val[-45000:]

    ws.update_cell(row, COL_LOGS, new_val)


def set_cell(chat_id: int, col: int, value: str):
    if not _ensure_ws():
        return
    row = get_or_create_user_row(chat_id)
    if not row:
        return
    ws.update_cell(row, col, value)
    _touch_last_active(chat_id)


def get_cell(chat_id: int, col: int) -> str:
    if not _ensure_ws():
        return ""
    row = get_or_create_user_row(chat_id)
    if not row:
        return ""
    return (ws.cell(row, col).value or "").strip()


def set_status(chat_id: int, status: str):
    set_cell(chat_id, COL_STATUS, status)


def get_status(chat_id: int) -> str:
    return get_cell(chat_id, COL_STATUS)


def set_stage(chat_id: int, stage: str):
    set_cell(chat_id, COL_STAGE, stage)


def get_stage(chat_id: int) -> str:
    return get_cell(chat_id, COL_STAGE)


def set_dialog_step(chat_id: int, step: str):
    set_cell(chat_id, COL_DIALOG_STEP, step)


def get_dialog_step(chat_id: int) -> str:
    v = get_cell(chat_id, COL_DIALOG_STEP)
    return v if v else "idle"


def set_question_cat(chat_id: int, cat: str):
    set_cell(chat_id, COL_QUESTION_CAT, cat)


def get_question_cat(chat_id: int) -> str:
    v = get_cell(chat_id, COL_QUESTION_CAT)
    return v if v else "unknown"


def reset_dialog(chat_id: int):
    set_dialog_step(chat_id, "idle")
    set_question_cat(chat_id, "")


def set_fio(chat_id: int, fio: str):
    set_cell(chat_id, COL_FIO, fio)


# ----------------------------
# Menus
# ----------------------------
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📌 Адаптация"))
    markup.add(types.KeyboardButton("🎯 Цели ИС"))
    markup.add(types.KeyboardButton("❓ Задать вопрос"))
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup


def adaptation_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ План на 1-й день"))
    markup.add(types.KeyboardButton("📅 План на 1-ю неделю"))
    markup.add(types.KeyboardButton("🎯 План на 1 месяц"))
    markup.add(types.KeyboardButton("🧾 Документы / доступы (чеклист)"))
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup


def question_category_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔐 Мои логины и пароли"))
    markup.add(types.KeyboardButton("⏱️ Организация и оплата рабочего времени"))
    markup.add(types.KeyboardButton("🧩 Рабочие процессы и задачи"))
    markup.add(types.KeyboardButton("📝 Другое"))
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup


# ----------------------------
# Commands
# ----------------------------
@bot.message_handler(commands=["start"])
def start_cmd(message):
    chat_id = message.chat.id

    # гарантируем строку
    _ = get_or_create_user_row(chat_id)

    step = get_dialog_step(chat_id)
    status = get_status(chat_id)

    # resume диалога
    if step == "wait_name":
        bot.send_message(chat_id, "Продолжим 🙂 Напиши, пожалуйста, своё ФИО:")
        append_log(chat_id, "resume", {"step": "wait_name"})
        return

    if step == "wait_question_category":
        bot.send_message(chat_id, "Продолжим 🙂 Выбери тему вопроса:", reply_markup=question_category_menu())
        append_log(chat_id, "resume", {"step": "wait_question_category"})
        return

    if step == "wait_question":
        bot.send_message(chat_id, "Продолжим 🙂 Напиши вопрос одним сообщением:")
        append_log(chat_id, "resume", {"step": "wait_question", "cat": get_question_cat(chat_id)})
        return

    # стандартное поведение
    if status in ["Проходит адаптацию", "Адаптация начата"]:
        bot.send_message(chat_id, "Продолжим адаптацию 👇", reply_markup=adaptation_menu())
        append_log(chat_id, "start", {"status": status})
        return

    if status == "Есть вопрос":
        bot.send_message(chat_id, "У тебя есть зафиксированный вопрос. Можешь задать ещё один 👇", reply_markup=main_menu())
        append_log(chat_id, "start", {"status": status})
        return

    bot.send_message(chat_id, "Привет 👋 Выбери раздел:", reply_markup=main_menu())
    append_log(chat_id, "start", {"status": status or "Новый"})


@bot.message_handler(commands=["menu"])
def menu_cmd(message):
    chat_id = message.chat.id
    reset_dialog(chat_id)
    bot.send_message(chat_id, "Главное меню:", reply_markup=main_menu())
    append_log(chat_id, "menu")


@bot.message_handler(commands=["help"])
def help_cmd(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "Я HR-ассистент.\n\n"
        "Что умею сейчас:\n"
        "• 📌 Адаптация — запуск и планы\n"
        "• ❓ Вопрос — зафиксировать вопрос для HR\n\n"
        "Если кнопки пропали — нажми /menu.",
        reply_markup=main_menu()
    )
    append_log(chat_id, "help")


@bot.message_handler(commands=["status"])
def status_cmd(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "✅ Я онлайн и работаю.")
    append_log(chat_id, "status")


# ----------------------------
# Messages
# ----------------------------
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = (message.text or "").strip()

    # ensure row + last active
    _ = get_or_create_user_row(chat_id)
    _touch_last_active(chat_id)

    # universal back
    if text == "⬅️ Назад":
        reset_dialog(chat_id)
        bot.send_message(chat_id, "Главное меню:", reply_markup=main_menu())
        append_log(chat_id, "back_to_menu")
        return

    # adaptation sub-menu
    if text in ["✅ План на 1-й день", "📅 План на 1-ю неделю", "🎯 План на 1 месяц", "🧾 Документы / доступы (чеклист)"]:
        bot.send_message(chat_id, f"{text}\n\nКонтент будет доработан позже.")
        append_log(chat_id, "open_adaptation_section", {"section": text})

        # stage marker (optional)
        if text == "✅ План на 1-й день":
            set_stage(chat_id, "День 1")
        elif text == "📅 План на 1-ю неделю":
            set_stage(chat_id, "Неделя 1")
        elif text == "🎯 План на 1 месяц":
            set_stage(chat_id, "Месяц 1")
        else:
            # чеклист не меняет этап
            pass

        return

    # start adaptation
    if text == "📌 Адаптация":
        set_dialog_step(chat_id, "wait_name")
        bot.send_message(chat_id, "Напиши, пожалуйста, своё ФИО:")
        append_log(chat_id, "adaptation_start")
        set_status(chat_id, "Проходит адаптацию")
        set_stage(chat_id, "День 1")
        return

    # capture name
    if get_dialog_step(chat_id) == "wait_name":
        fio = text
        set_dialog_step(chat_id, "idle")

        bot.send_message(
            chat_id,
            f"Отлично, {fio}!\n\n"
            "✅ Адаптация запущена.\n"
            "Я буду сопровождать тебя в течение испытательного срока.\n\n"
            "С чего начнём?",
            reply_markup=adaptation_menu()
        )

        set_fio(chat_id, fio)
        set_status(chat_id, "Адаптация начата")
        append_log(chat_id, "name_captured", {"fio": fio})
        return

    # goals placeholder
    if text == "🎯 Цели ИС":
        bot.send_message(chat_id, "🎯 Тут будут цели на испытательный срок (ИПИ).")
        append_log(chat_id, "open_goals")
        return

    # question flow
    if text == "❓ Задать вопрос":
        set_dialog_step(chat_id, "wait_question_category")
        bot.send_message(chat_id, "Выбери тему вопроса:", reply_markup=question_category_menu())
        append_log(chat_id, "ask_question_start")
        return

    if get_dialog_step(chat_id) == "wait_question_category":
        categories = {
            "🔐 Мои логины и пароли": "logins",
            "⏱️ Организация и оплата рабочего времени": "work_time",
            "🧩 Рабочие процессы и задачи": "processes",
            "📝 Другое": "other",
        }

        if text in categories:
            cat = categories[text]
            set_question_cat(chat_id, cat)
            set_dialog_step(chat_id, "wait_question")

            bot.send_message(chat_id, "Ок! Напиши вопрос одним сообщением:")
            append_log(chat_id, "question_category_selected", {"cat": cat})
            return

        bot.send_message(chat_id, "Выбери тему вопроса кнопкой ниже:", reply_markup=question_category_menu())
        return

    if get_dialog_step(chat_id) == "wait_question":
        q = text
        cat = get_question_cat(chat_id)

        reset_dialog(chat_id)

        bot.send_message(chat_id, "✅ Принято!", reply_markup=main_menu())
        append_log(chat_id, "question_captured", {"cat": cat, "q": q[:200]})
        set_status(chat_id, "Есть вопрос")
        return

    # fallback
    bot.send_message(chat_id, "Я понимаю только кнопки меню 🙂 Нажми /menu, если кнопки пропали.")


# ----------------------------
# ----------------------------
# Start (инициализация)
# ----------------------------
init_sheets()

# В webhook-режиме (Hugging Face / FastAPI) polling НЕ запускаем.
# Polling оставляем только для локального теста, когда ты запускаешь bot.py вручную.
if __name__ == "__main__":
    print("Bot started (local polling)...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)