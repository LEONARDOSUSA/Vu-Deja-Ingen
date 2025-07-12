# main.py

import pytz
from datetime import datetime

# Importar módulos por nombre real
from signals_bot import run as señales_apertura
from signals_bot1 import run as señales_post_apertura
from signals2_bot import run as señales_post_10am

# Configuración de zona horaria
NY_TZ = pytz.timezone("America/New_York")
hoy = datetime.now(NY_TZ).date()
ahora = datetime.now(NY_TZ)

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

    print("\n🏁 Ciclo institucional completo — Vu Deja Ingen finalizado 🔐")

if __name__ == "__main__":
    ejecutar_vu_deja_ingen()
