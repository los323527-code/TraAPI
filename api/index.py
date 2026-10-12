import os
import re
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="TraAPI Music Bot", version="2.0.0")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


async def telegram(method: str, data: dict):
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Telegram bot token is not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=data,
        )
    if r.is_error or not r.json().get("ok"):
        raise HTTPException(status_code=502, detail="Telegram API request failed")
    return r.json()["result"]


async def send_text(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = {"inline_keyboard": keyboard}
    await telegram("sendMessage", data)


async def search_youtube(query: str):
    if not YOUTUBE_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "type": "video",
                "maxResults": 5,
                "q": query,
                "key": YOUTUBE_API_KEY,
            },
        )
    if r.is_error:
        return []
    items = r.json().get("items", [])
    return [
        {
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "url": "https://www.youtube.com/watch?v=" + item["id"]["videoId"],
        }
        for item in items
        if item.get("id", {}).get("videoId")
    ]


class NotifyBody(BaseModel):
    message: str


@app.get("/")
async def root():
    return {"ok": True, "service": "TraAPI Music Bot"}


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.post("/api/notify")
async def notify(body: NotifyBody, x_webhook_secret: str | None = Header(default=None)):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    if not CHAT_ID:
        raise HTTPException(status_code=500, detail="TELEGRAM_CHAT_ID is not configured")
    await send_text(CHAT_ID, body.message[:4000])
    return {"ok": True, "sent": True}


@app.post("/api/telegram")
async def telegram_update(request: Request):
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return {"ok": True}

    if text.startswith("/start"):
        await send_text(
            chat_id,
            "សួស្តី! 🎵 ខ្ញុំជា TraAPI Music Bot។\n\n"
            "វាយ /search ឈ្មោះបទ ដើម្បីស្វែងរកចម្រៀង។\n"
            "ឧទាហរណ៍៖ /search ចម្រៀងខ្មែរ\n\n"
            "ខ្ញុំផ្តល់តំណស្តាប់ពី YouTube។ MP3 អាចផ្ញើបានតែពីប្រភពដែលអ្នកមានសិទ្ធិប្រើ។"
        )
        return {"ok": True}

    if text.startswith("/search"):
        query = text[len("/search"):].strip()
    elif text.startswith("/"):
        await send_text(chat_id, "ប្រើ៖ /search ឈ្មោះបទ\nឧទាហរណ៍៖ /search ចម្រៀងខ្មែរ")
        return {"ok": True}
    else:
        query = text

    if not query:
        await send_text(chat_id, "សូមបញ្ចូលឈ្មោះបទ។ ឧទាហរណ៍៖ /search ចម្រៀងខ្មែរ")
        return {"ok": True}

    results = await search_youtube(query[:150])
    if results is None:
        await send_text(chat_id, "មិនទាន់កំណត់ YOUTUBE_API_KEY នៅ Vercel ទេ។")
        return {"ok": True}
    if not results:
        await send_text(chat_id, "រកមិនឃើញលទ្ធផល ឬ YouTube API មានបញ្ហា។ សូមសាកម្ដងទៀត។")
        return {"ok": True}

    keyboard = []
    lines = ["🎵 លទ្ធផលស្វែងរក៖"]
    for i, item in enumerate(results, 1):
        title = re.sub(r"[<>]", "", item["title"])[:180]
        channel = re.sub(r"[<>]", "", item["channel"])[:100]
        lines.append(f"{i}. {title}\n   Channel: {channel}")
        keyboard.append([{"text": f"▶️ ស្តាប់បទ {i}", "url": item["url"]}])

    await send_text(chat_id, "\n\n".join(lines), keyboard)
    return {"ok": True}


@app.post("/api/send-audio")
async def send_audio(request: Request, x_webhook_secret: str | None = Header(default=None)):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    body = await request.json()
    chat_id = body.get("chat_id") or CHAT_ID
    audio_url = body.get("audio_url", "")

    # Only accept direct HTTPS MP3/M4A URLs from authorized sources.
    if not isinstance(audio_url, str) or not re.match(r"^https://", audio_url):
        raise HTTPException(status_code=400, detail="audio_url must be HTTPS")
    if not re.search(r"\.(mp3|m4a)(?:\?.*)?$", audio_url, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Provide a direct MP3/M4A URL")
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required")

    await telegram("sendAudio", {"chat_id": chat_id, "audio": audio_url})
    return {"ok": True, "sent": True}
