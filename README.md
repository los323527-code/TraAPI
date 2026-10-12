# Tradownload Telegram Webhook API (FastAPI + Vercel)

This is a small FastAPI service for Telegram notifications. It is a separate service; it does not convert the original NestJS/yt-dlp downloader into FastAPI.

## Routes
- `GET /` service status
- `GET /api/health` health check
- `POST /api/notify` sends a Telegram message; requires `x-webhook-secret`
- `POST /api/telegram` receives Telegram webhook updates and replies to `/start` or text messages

## Environment variables
Set these in Vercel Project Settings > Environment Variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` (your personal chat ID for notifications)
- `WEBHOOK_SECRET` (a long random secret for `/api/notify`)

Do not commit `.env` or real tokens to GitHub.

## Configure Telegram webhook
After deployment, open this URL in a browser, replacing values locally (do not share the token):
`https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR-PROJECT.vercel.app/api/telegram`

Check webhook info:
`https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

## Test notify endpoint
POST JSON to `https://YOUR-PROJECT.vercel.app/api/notify` with header `x-webhook-secret: YOUR_WEBHOOK_SECRET` and body `{"message":"Test from API"}`.

## Deploy to Vercel
Import this GitHub repository on https://vercel.com/new, keep the root directory at repository root, and deploy. Add the environment variables before/after deploy, then redeploy if needed.

Vercel serverless functions are not a persistent worker. This project only handles HTTP requests and Telegram notifications; it does not run long downloads or keep background jobs alive.
