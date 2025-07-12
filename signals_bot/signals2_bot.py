import os
from dotenv import load_dotenv
import pytz
import ta
import requests
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import pandas as pd

# 🔐 Cargar entorno y claves
load_dotenv()
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://paper-api.alpaca.markets"
NY_TZ = pytz.timezone("America/New_York")

if ALPACA_KEY and ALPACA_SECRET:
    os.environ["APCA_API_KEY_ID"] = ALPACA_KEY
    os.environ["APCA_API_SECRET_KEY"] = ALPACA_SECRET
else:
    print("⛔ Error: claves Alpaca no definidas")
    exit()

api = tradeapi.REST(base_url=BASE_URL)
tickers_activos = ["AAPL", "SPY", "TSLA", "MSFT", "NVDA", "AMD"]
SEC_LIMPIA = True
TEST_MODE = False
FECHA_TEST = "2025-07-02"

def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def obtener_df(tf, ticker, momento_final):
    cierre = momento_final - timedelta(minutes=1 if tf == "1Min" else 5 if tf == "5Min" else 15)
    inicio = cierre - timedelta(minutes=600)
    df = api.get_bars(ticker, tf, start=inicio.isoformat(), end=cierre.isoformat()).df
    return df.tz_convert("America/New_York").dropna()

def diagnostico_macd(ticker, momento, direccion):
    marcos = ["1Min", "5Min", "15Min"]
    confirmados = 0
    for tf in marcos:
        try:
            df = obtener_df(tf, ticker, momento)
            if df.empty or len(df) < 35:
                print(f"📊 MACD {tf} ➝ ❌ Datos insuficientes")
                continue
            macd = ta.trend.MACD(df["close"])
            m1 = macd.macd().iloc[-1]
            s1 = macd.macd_signal().iloc[-1]
            alineado = (m1 > s1) if direccion == "CALL" else (m1 < s1)
            estado = "✅ alineado" if alineado else "❌ no alineado"
            print(f"📊 MACD {tf} ➝ MACD={round(m1,4)}, Signal={round(s1,4)} ➝ {estado}")
            if alineado:
                confirmados += 1
        except Exception as e:
            print(f"📊 MACD {tf} ➝ ⚠️ error: {e}")
    return confirmados

def validar_sma(df, direccion, marco):
    try:
        if df.empty or len(df) < 30:
            print(f"📏 SMA {marco} ➝ ❌ Datos insuficientes")
            return False
        sma20 = ta.trend.sma_indicator(df["close"], window=20)
        sma30 = ta.trend.sma_indicator(df["close"], window=30)
        p = df["close"].iloc[-1]
        s20 = sma20.iloc[-1]
        s30 = sma30.iloc[-1]
        if pd.isna(s20) or pd.isna(s30):
            print(f"📏 SMA {marco} ➝ ⚠️ SMA incompleta ➝ marco omitido")
            return False
        alineadas = (
            p > s20 and p > s30 and s20 > s30 if direccion == "CALL"
            else p < s20 and p < s30 and s20 < s30
        )
        estado = "✅ alineadas" if alineadas else "❌ no alineadas"
        print(f"📏 SMA {marco} ➝ Precio={round(p,2)}, SMA20={round(s20,2)}, SMA30={round(s30,2)} ➝ {estado}")
        return alineadas
    except Exception as e:
        print(f"📏 SMA {marco} ➝ ⚠️ error: {e}")
        return False
def detectar_direccion_ruptura(ticker, fecha, hora_a, hora_b):
    ini_a = NY_TZ.localize(datetime.combine(fecha, datetime.strptime(hora_a, "%H:%M").time()))
    fin_a = ini_a + timedelta(minutes=15)
    ini_b = NY_TZ.localize(datetime.combine(fecha, datetime.strptime(hora_b, "%H:%M").time()))
    fin_b = ini_b + timedelta(minutes=15)

    df_a = api.get_bars(ticker, "15Min", start=ini_a.isoformat(), end=fin_a.isoformat()).df
    df_b = api.get_bars(ticker, "15Min", start=ini_b.isoformat(), end=fin_b.isoformat()).df
    if df_a.empty or df_b.empty:
        print("⛔ Velas no disponibles para ruptura")
        return None

    va = df_a.iloc[0]
    vb = df_b.iloc[0]
    print(f"\n📊 Comparando ruptura entre {hora_a} y {hora_b}")
    print(f"📉 Vela A ➝ open={round(va['open'],2)}, close={round(va['close'],2)}")
    print(f"📈 Vela B ➝ open={round(vb['open'],2)}, close={round(vb['close'],2)}")

    if vb["close"] > va["close"] and vb["close"] > va["open"]:
        print("📍 Dirección ➝ CALL confirmada")
        return "CALL"
    elif vb["close"] < va["close"] and vb["close"] < va["open"]:
        print("📍 Dirección ➝ PUT confirmada")
        return "PUT"
    else:
        print("⛔ Ruptura aún no confirmada")
        return None

def validar_secuencia_dos_velas(ticker, fecha, horas, direccion):
    cuerpo_validas = 0
    for hora in horas:
        ini = NY_TZ.localize(datetime.combine(fecha, datetime.strptime(hora, "%H:%M").time()))
        fin = ini + timedelta(minutes=15)
        df = api.get_bars(ticker, "15Min", start=ini.isoformat(), end=fin.isoformat()).df
        if df.empty:
            print(f"⛔ Sin datos para vela {hora}")
            continue

        v = df.iloc[0]
        cuerpo = abs(v["close"] - v["open"])
        rango = v["high"] - v["low"]
        pct = cuerpo / rango if rango > 0 else 0
        print(f"🕒 Vela {hora} ➝ cuerpo={round(cuerpo,2)}, rango={round(rango,2)}, pct={round(pct,2)}")

        if direccion == "CALL" and v["close"] > v["open"] and pct > 0.5:
            cuerpo_validas += 1
        elif direccion == "PUT" and v["close"] < v["open"] and pct > 0.5:
            cuerpo_validas += 1

    return cuerpo_validas == 2

def evaluar_calidad_senal(ticker, momento, direccion):
    try:
        df = obtener_df("1Min", ticker, momento)
        vela = df.iloc[-1]
        cuerpo = abs(vela["close"] - vela["open"])
        rango = vela["high"] - vela["low"]
        pct = cuerpo / rango if rango > 0 else 0

        macd = ta.trend.MACD(df["close"])
        impulso = abs(macd.macd().iloc[-1] - macd.macd_signal().iloc[-1])

        sma20 = ta.trend.sma_indicator(df["close"], window=20).iloc[-1]
        dif_sma = abs(vela["close"] - sma20)

        puntaje = round(pct * 2 + impulso + dif_sma * 0.5, 4)
        return puntaje
    except Exception:
        return 0.0
def evaluar_senal_institucional(ticker, fecha, hora_a, hora_b, momento):
    direccion = detectar_direccion_ruptura(ticker, fecha, hora_a, hora_b)
    if not direccion:
        return False

    horas_secuencia = [hora_a, hora_b]
    if SEC_LIMPIA and not validar_secuencia_dos_velas(ticker, fecha, horas_secuencia, direccion):
        print("⛔ Secuencia institucional incompleta ➝ sin señal\n")
        return False

    sma_total = sum([
        validar_sma(obtener_df(tf, ticker, momento), direccion, tf)
        for tf in ["1Min", "5Min", "15Min"]
    ])
    macd_total = diagnostico_macd(ticker, momento, direccion)

    print("\n🧠 Resultado táctico:")
    print(f"✔️ Dirección ➝ {direccion}")
    print(f"{'✔️' if sma_total >= 2 else '❌'} SMA ➝ {sma_total}/3 marcos válidos")
    print(f"{'✔️' if macd_total >= 2 else '❌'} MACD ➝ {macd_total}/3 marcos confirmados")

    if sma_total >= 2 and macd_total >= 2:
        precio_ejecucion = round(obtener_df("15Min", ticker, momento)["close"].iloc[-1], 2)
        puntaje_tecnico = evaluar_calidad_senal(ticker, momento, direccion)

        mensaje = f"""
📡 *Señal institucional detectada*

🔹 *Ticker:* `{ticker}`  
🔹 *Dirección:* `{direccion}`  
🔹 *Precio ejecución:* `${precio_ejecucion}`  
🔹 *MACD alineado:* `{macd_total}/3 marcos`  
🔹 *SMA:* `{sma_total}/3 marcos alineados`

📊 *Diagnóstico técnico:*  
✔️ Cuerpo dominante en velas 15Min  
✔️ Momentum multitimeframe validado  
✔️ Filtros SMA y MACD cumplidos

🧭 *Oportunidad táctica intradía confirmada*  
⚖️ *Puntaje técnico:* `{puntaje_tecnico}`
"""
        enviar_mensaje(mensaje)

        # 📡 Enviar mensaje con contratos sugeridos por IBKR
        señal = {"ticker": ticker, "direccion": direccion}
        contratos = obtener_contratos_ibkr(señal)

        mensaje_selector = f"\n🎯 *Contratos sugeridos para `{ticker}` ({direccion})*\n"
        for idx, c in enumerate(contratos[:3], start=1):
            mensaje_selector += f"\n━━━━━━━━━━━━━━━━\n⚡ *Opción #{idx}:* `{c['symbol']}`"
            mensaje_selector += f"\n📅 Vencimiento: `{c['expiration']}` | Strike: `{c['strike']}`"
            mensaje_selector += f"\n📊 Delta: `{c['delta']}` | IV: `{c['iv']}` | Volumen: `{c['volume']}`"
            mensaje_selector += f"\n💸 Spread: `{c['spread']}` | Precio: `${c['precio']}`"

        mensaje_selector += "\n\n🔐 *Diagnóstico institucional vía Vu Deja Contracts™*"
        enviar_mensaje(mensaje_selector)

        print("📨 Señal y contratos enviados por Telegram\n")
        return True
    elif macd_total >= 2:
        print("🟡 Señal semi institucional detectada (MACD confirmado, SMA parcial)\n")
    else:
        print("⛔ Condiciones incompletas ➝ sin señal\n")
    return False

# 🎬 Ciclo principal de ruptura progresiva
if __name__ == "__main__":
    ahora = datetime.now(NY_TZ)
    fecha = datetime.strptime(FECHA_TEST, "%Y-%m-%d").date() if TEST_MODE else ahora.date()

    horarios = [
        ("09:30", "09:45"),
        ("10:00", "10:15"),
        ("10:15", "10:30"),
        ("10:30", "10:45"),
        ("10:45", "11:00")
    ]

    print("✅ Bot institucional con ruptura progresiva ejecutando\n")
    for ticker in tickers_activos:
        señal_emitida = False
        for hora_a, hora_b in horarios:
            momento = NY_TZ.localize(datetime.combine(fecha, datetime.strptime(hora_b, "%H:%M").time()))
            margen_cierre = momento + timedelta(minutes=1)

            if ahora < margen_cierre:
                print(f"⏳ Vela {hora_b} aún no cerrada ➝ esperando hasta {margen_cierre.strftime('%H:%M')} NY\n")
                continue

            print(f"🔁 Evaluando ruptura {hora_a} ➝ {hora_b} para {ticker}")
            if evaluar_senal_institucional(ticker, fecha, hora_a, hora_b, momento):
                señal_emitida = True
                break
        if not señal_emitida:
            print(f"📉 No se emitió señal para {ticker}\n")

    print("🏁 Diagnóstico finalizado\n")
