import os
import requests

def enviar_mensaje_telegram(texto, chat_id):
    token = os.getenv("TELEGRAM_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    return response.status_code
