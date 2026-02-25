import os
import telebot
from telebot import types

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN not set")

bot = telebot.TeleBot(TOKEN)

# Память на время работы бота (позже заменим на таблицу/БД)
users = {}


def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📌 Адаптация"))
    markup.add(types.KeyboardButton("🎯 Цели ИС"))
    markup.add(types.KeyboardButton("❓ Задать вопрос"))
    return markup


@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.send_message(
        message.chat.id,
        "Привет 👋 Я HR-ассистент.\nВыбери раздел:",
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = (message.text or "").strip()

    # 1) Нажали "Адаптация" -> спрашиваем ФИО
    if text == "📌 Адаптация":
        users[chat_id] = {"step": "wait_name"}
        bot.send_message(chat_id, "Давай начнём адаптацию 👌\nНапиши, пожалуйста, своё ФИО:")
        return

    # 2) Ждём ФИО
    if chat_id in users and users[chat_id].get("step") == "wait_name":
        users[chat_id]["name"] = text
        users[chat_id]["step"] = "done"
        bot.send_message(chat_id, f"Отлично, {text}!\n✅ Я записал твоё имя.\nВыбери, что дальше:", reply_markup=main_menu())
        return

    # 3) Остальные кнопки
    if text == "🎯 Цели ИС":
        bot.send_message(chat_id, "🎯 Тут будут цели на испытательный срок (ИПИ).")
        return

    if text == "❓ Задать вопрос":
        bot.send_message(chat_id, "❓ Напиши вопрос одним сообщением. Я зафиксирую его для HR.")
        return

    # 4) Фолбек
    bot.send_message(chat_id, "Я пока понимаю только кнопки меню 🙂 Нажми /start, если меню пропало.")


print("Bot started...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)