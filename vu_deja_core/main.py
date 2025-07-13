import pytz
from datetime import datetime
import os

# Importar señales y módulos institucionales
from signals_bot import run as señales_apertura
from signals_bot1 import run as señales_post_apertura
from signals2_bot import run as señales_post_10am
from entregador_selector import generar_mensajes_por_nivel
from mensajero_telegram import enviar_mensaje_telegram

# 📡 Función que genera y envía mensajes por cliente
def entregar_a_cliente(signal_data, nivel_cliente, client_id):
    chat_id = os.getenv(f"TELEGRAM_CHAT_ID_{client_id}")
    mensajes = generar_mensajes_por_nivel(signal_data, nivel_cliente, client_id)

    for msg in mensajes:
        print(msg)  # 🖥️ Terminal
        enviar_mensaje_telegram(msg, chat_id)  # 📲 Telegram

# 🕒 Configuración de zona horaria
NY_TZ = pytz.timezone("America/New_York")
hoy = datetime.now(NY_TZ).date()
ahora = datetime.now(NY_TZ)

# 🚀 Ejecución institucional
def ejecutar_vu_deja_ingen():
    print(f"\n🚀 Vu Deja Ingen operativo 🗓️ {hoy} 🕒 {ahora.strftime('%H:%M')} NY\n")

    # 🟣 Fase 1 — Apertura institucional
    print("🔍 Ejecutando signals_bot.py (apertura 09:30–09:35)\n")
    señales_apertura()

    # 🔵 Fase 2 — Diagnóstico post apertura
    print("\n🔍 Ejecutando signals_bot1.py (escaneo post 09:45)\n")
    señales_post_apertura()

    # 🔴 Fase 3 — Señales avanzadas después de 10:00 AM
    print("\n🔍 Ejecutando signals2_bot.py (diagnóstico post 10:00 AM)\n")
    señales_post_10am()

    # 💼 Ejemplo de entrega institucional manual (simulación)
    signal_ejemplo = {"ticker": "AAPL", "direccion": "PUT"}
    entregar_a_cliente(signal_ejemplo, "intermedio", 1003)
    entregar_a_cliente(signal_ejemplo, "premium", 1001)

    print("\n🏁 Ciclo institucional completo — Vu Deja Ingen finalizado 🔐")

# 🔧 Activación por consola
if __name__ == "__main__":
    ejecutar_vu_deja_ingen()
