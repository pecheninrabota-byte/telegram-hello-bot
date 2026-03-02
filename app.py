import os
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import PlainTextResponse

# импортируем твой bot.py
import bot as bot_module

# достаем объект TeleBot из bot.py
tg_bot = getattr(bot_module, "bot", None)
if tg_bot is None:
    raise RuntimeError(
        "В bot.py не найден объект TeleBot. Ожидаю переменную `bot = telebot.TeleBot(...)`"
    )

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
SECRET_HEADER_NAME = "X-Telegram-Bot-Api-Secret-Token"

app = FastAPI()


# Railway health-check (корень)
@app.get("/")
async def root_health():
    return {"status": "ok"}


# дополнительный health (можно оставить, полезно для ручной проверки)
@app.get("/health", response_class=PlainTextResponse)
async def health_text():
    return "ok"


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias=SECRET_HEADER_NAME),
):
    # 1) Проверяем секрет (если задан)
    if WEBHOOK_SECRET:
        if (not x_telegram_bot_api_secret_token) or (x_telegram_bot_api_secret_token != WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # 2) Забираем update от Telegram
    data = await request.json()

    # 3) Передаём update в telebot
    from telebot import types
    update = types.Update.de_json(data)
    tg_bot.process_new_updates([update])

    return {"ok": True}