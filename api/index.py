import os
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Tradownload Telegram Webhook API", version="1.0.0")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

async def telegram_send(text: str, chat_id: str | None = None):
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN is not configured")
    target = chat_id or CHAT_ID
    if not target:
        raise HTTPException(status_code=500, detail="TELEGRAM_CHAT_ID is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": target, "text": text[:4000], "disable_web_page_preview": True},
        )
    if r.is_error:
        raise HTTPException(status_code=502, detail="Telegram API request failed")
    result = r.json()
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail="Telegram rejected the message")
    return {"ok": True}

class NotifyBody(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"ok": True, "service": "Tradownload Telegram Webhook API"}

@app.get("/api/health")
async def health():
    return {"ok": True}

@app.post("/api/notify")
async def notify(body: NotifyBody, x_webhook_secret: str | None = Header(default=None)):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    await telegram_send(body.message)
    return {"ok": True, "sent": True}

@app.post("/api/telegram")
async def telegram_update(request: Request):
    # Configure Telegram webhook to this URL. Reply to messages sent to the bot.
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    incoming = (message.get("text") or "").strip()
    if incoming == "/start":
        await telegram_send("សួស្តី! Telegram Bot របស់អ្នកដំណើរការហើយ។", str(chat_id))
    elif incoming:
        await telegram_send(f"ទទួលបានសារ៖ {incoming}", str(chat_id))
    return {"ok": True}
