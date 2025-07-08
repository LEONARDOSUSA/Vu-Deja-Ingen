import os
import pytz
import ta
import requests
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta

# 🔐 Cargar entorno desde .env
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://paper-api.alpaca.markets"
NY_TZ = pytz.timezone("America/New_York")
api = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, base_url=BASE_URL)

tickers_activos = ["AAPL", "SPY", "TSLA", "MSFT", "NVDA", "AMD"]
ya_enviados = set()

def verificar_claves_y_datos(key, secret):
    try:
        test_api = tradeapi.REST(key, secret, base_url=BASE_URL)
        account = test_api.get_account()
        return account.status == "ACTIVE"
    except Exception:
        return False

def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def evaluar_ticker(ticker, fecha, momento):
    if ticker in ya_enviados:
        print(f"⏹️ {ticker} ya procesado — se omite\n")
        return

    print(f"\n📡 Evaluando {ticker} @ 09:36 NY...")

    inicio = NY_TZ.localize(datetime.combine(fecha, datetime.strptime("09:00", "%H:%M").time()))
    fin = NY_TZ.localize(datetime.combine(fecha, datetime.strptime("09:33", "%H:%M").time()))
    df = api.get_bars(ticker, "1Min", start=inicio.isoformat(), end=fin.isoformat()).df.tz_convert("America/New_York")
    df_apertura = df.between_time("09:30", "09:32")

    if df_apertura.empty or len(df_apertura) < 3:
        print("⛔ No hay suficientes velas ➝ se omite análisis")
        return

    o, c = df_apertura["open"].values, df_apertura["close"].values
    direccion = None

    if c[0] > o[0] and c[1] > o[1] and c[1] > c[0] and c[2] > c[0] and c[2] > o[1]:
        direccion = "CALL"
    elif c[0] < o[0] and c[1] < o[1] and c[1] < c[0] and c[2] < c[0] and c[2] < o[1]:
        direccion = "PUT"

    print(f"📍 Dirección ➝ {direccion if direccion else '❌ No definida'}")
    if not direccion:
        return

    # 📏 SMA institucional — 1Min
    df["sma20"] = ta.trend.sma_indicator(df["close"], window=20)
    df["sma30"] = ta.trend.sma_indicator(df["close"], window=30)
    precio_1m = df["close"].iloc[-1]
    sma20_1m = df["sma20"].iloc[-1]
    sma30_1m = df["sma30"].iloc[-1]
    sma_valida_1m = (
        precio_1m > sma20_1m and precio_1m > sma30_1m and sma20_1m > sma30_1m
        if direccion == "CALL"
        else precio_1m < sma20_1m and precio_1m < sma30_1m and sma20_1m < sma30_1m
    )

    # 📏 SMA institucional — 5Min
    inicio_5m = NY_TZ.localize(datetime.combine(fecha, datetime.strptime("07:00", "%H:%M").time()))
    df_5m = api.get_bars(ticker, "5Min", start=inicio_5m.isoformat(), end=momento.isoformat()).df.tz_convert("America/New_York")
    df_5m["sma20"] = ta.trend.sma_indicator(df_5m["close"], window=20)
    df_5m["sma30"] = ta.trend.sma_indicator(df_5m["close"], window=30)
    precio_5m = df_5m["close"].iloc[-1]
    sma20_5m = df_5m["sma20"].iloc[-1]
    sma30_5m = df_5m["sma30"].iloc[-1]
    sma_valida_5m = (
        precio_5m > sma20_5m and precio_5m > sma30_5m and sma20_5m > sma30_5m
        if direccion == "CALL"
        else precio_5m < sma20_5m and precio_5m < sma30_5m and sma20_5m < sma30_5m
    )

    print(f"📏 SMA ➝ {'✅' if sma_valida_1m and sma_valida_5m else '❌'}")

    def diagnostico_macd(marco):
        try:
            ts = momento.replace(second=0)
            ajuste = {"5Min": 5, "15Min": 15}
            if marco in ajuste:
                ts -= timedelta(minutes=ts.minute % ajuste[marco])
            ts -= timedelta(minutes=1)
            inicio = NY_TZ.localize((ts - timedelta(minutes=600)).replace(tzinfo=None))
            df_tf = api.get_bars(ticker, marco, start=inicio.isoformat(), end=ts.isoformat()).df.tz_convert("America/New_York").dropna()
            if len(df_tf) < 35:
                return False
            macd = ta.trend.MACD(df_tf["close"])
            return macd.macd().iloc[-1] > macd.macd_signal().iloc[-1] if direccion == "CALL" else macd.macd().iloc[-1] < macd.macd_signal().iloc[-1]
        except:
            return False

    confirmados = sum([diagnostico_macd(tf) for tf in ["1Min", "5Min", "15Min"]])
    print(f"📊 MACD ➝ {confirmados}/3")

    if sma_valida_1m and sma_valida_5m and confirmados >= 2:
        precio_senal = round(c[2], 2)
        mensaje = f"""
📡 *Señal institucional detectada*

🔹 *Ticker:* `{ticker}`  
🔹 *Dirección:* `{direccion}`  
🔹 *Precio señal:* `${precio_senal}`  
🔹 *MACD alineado:* `{confirmados}/3 marcos`  
🔹 *SMA:* `✅ Alineadas`

📊 *Diagnóstico técnico:*  
✔️ Patrón institucional confirmado en velas  
✔️ Momentum táctico validado  
✔️ Filtros SMA y MACD cumplidos

🧭 *Oportunidad táctica intradía confirmada*
"""
        enviar_mensaje(mensaje)
        ya_enviados.add(ticker)
        print("📨 Señal enviada por Telegram\n")
    else:
        print("⛔ Condiciones incompletas ➝ sin envío\n")

# 🎬 Ejecución principal
if __name__ == "__main__":
    print("🔐 Validando entorno Alpaca...")
    if not verificar_claves_y_datos(ALPACA_KEY, ALPACA_SECRET):
        print("⛔ Claves inválidas o sin acceso a datos Alpaca")
        exit()

    hora_actual = datetime.now(NY_TZ).time()
    hora_inicio = datetime.strptime("09:25", "%H:%M").time()
    hora_fin = datetime.strptime("09:46", "%H:%M").time()

    if hora_inicio <= hora_actual <= hora_fin:
        print("✅ Sistema activo — Ejecutando análisis institucional\n")
        fecha = datetime.now(NY_TZ).date()
        momento = NY_TZ.localize(datetime.combine(fecha, datetime.strptime("09:36", "%H:%M").time()))
        for ticker in tickers_activos:
            evaluar_ticker(ticker, fecha, momento)
        print("🏁 Diagnóstico finalizado para todos los tickers")
    else:
        print(f"⏳ Bot fuera de ventana operativa ({hora_actual.strftime('%H:%M')}) — no se ejecuta")
