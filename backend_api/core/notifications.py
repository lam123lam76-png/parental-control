import os
import logging
import threading
import requests as http_requests
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

def _dispatch_http(token: str, chat_id: str, text: str):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = http_requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5
        )
        if resp.status_code != 200:
            logger.warning(f"Telegram API responded with {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"Telegram dispatch failed: {e}")

def send_telegram_notification(db: Session, text: str):
    """
    Sends a Telegram notification asynchronously if Bot Token and Chat ID are configured.
    Pulls credentials from TelegramSetting table in DB or environment variables.
    """
    try:
        t_setting = db.query(models.TelegramSetting).first()
        token = (t_setting.bot_token if t_setting and t_setting.bot_token else None) or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = (t_setting.chat_id if t_setting and t_setting.chat_id else None) or os.getenv("TELEGRAM_CHAT_ID")
        
        if token and chat_id:
            # Dispatch asynchronously in daemon thread to avoid blocking request cycle
            threading.Thread(
                target=_dispatch_http,
                args=(token, chat_id, text),
                daemon=True
            ).start()
    except Exception as e:
        logger.warning(f"Failed to prepare Telegram notification: {e}")

