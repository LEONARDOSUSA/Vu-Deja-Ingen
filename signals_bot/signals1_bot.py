import os
import time
import requests
from datetime import datetime, timedelta
from validadores import verificar_claves_y_datos
import alpaca_trade_api as tradeapi
import pytz
import ta
from options_selector.options_selector_ibkr import obtener_contratos_ibkr  # ✅ Integrado

# 🔐 Configuración
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://paper-api.alpaca.markets"
api = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, base_url=BASE_URL)
NY_TZ = pytz.timezone("America/New_York")
tickers_activos = ["AAPL", "SPY", "TSLA", "MSFT", "NVDA", "AMD"]

# 📨 Enviar mensaje por Telegram
def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    requests.post(url, data=data)

# 🧱 Nivel + dirección institucional por vela 15Min
def obtener_nivel_15m(ticker, fecha_base):
    inicio = datetime.combine(fecha_base, datetime.strptime("09:30", "%H:%M").time())
    fin = inicio + timedelta(minutes=15)
    inicio = NY_TZ.localize(inicio)
    fin = NY_TZ.localize(fin)
    df = api.get_bars(ticker, "15Min", start=inicio.isoformat(), end=fin.isoformat()).df
    df = df.tz_convert("America/New_York")
    if df.empty:
        print(f"⛔ Sin vela 15Min para {ticker}")
        return None, None

    vela = df.iloc[0]
    close = vela["close"]
    open_ = vela["open"]
    if close > open_:
        direccion = "CALL"
    elif close < open_:
        direccion = "PUT"
    else:
        direccion = None

    print(f"· {ticker} ➝ Nivel 15Min: {round(close, 2)}, Dirección institucional: {direccion}")
    return round(close, 2), direccion

# 📊 Confirmación técnica MACD multitimeframe
def confirmar_macd(ticker, momento, direccion):
    timeframes = ["1Min", "5Min", "15Min"]
    confirmados = 0
    for tf in timeframes:
        try:
            inicio = momento - timedelta(minutes=600)
            inicio = NY_TZ.localize(inicio.replace(tzinfo=None))
            fin = NY_TZ.localize(momento.replace(tzinfo=None))
            df = api.get_bars(ticker, tf, start=inicio.isoformat(), end=fin.isoformat()).df
            df = df.tz_convert("America/New_York").dropna().copy()
            if len(df) < 35:
                print(f"· {tf}: ❌ Datos insuficientes — marco excluido")
                continue
            macd = ta.trend.MACD(df["close"])
            df["macd"], df["signal"] = macd.macd(), macd.macd_signal()
            df = df.dropna()
            m1, s1 = df["macd"].iloc[-1], df["signal"].iloc[-1]
            if direccion == "CALL" and m1 > s1:
                confirmados += 1
                print(f"· {tf}: ✅ MACD alineado (CALL)")
            elif direccion == "PUT" and m1 < s1:
                confirmados += 1
                print(f"· {tf}: ✅ MACD alineado (PUT)")
            else:
                print(f"· {tf}: ❌ MACD no alineado")
        except Exception as e:
            print(f"· {tf}: ⚠️ Error técnico → {e}")
    return confirmados >= 2
# 🔁 Loop principal institucional por nivel
def run():
    fecha_hoy = datetime.now(NY_TZ).date()
    niveles = {}
    direcciones_inst = {}
    enviados = set()
    print(f"📍 Esperando cierre de vela 15Min...", flush=True)

    while datetime.now(NY_TZ).time() < datetime.strptime("09:46", "%H:%M").time():
        time.sleep(10)

    # Cargar niveles institucionales para todos los tickers
    for ticker in tickers_activos:
        nivel, direccion_inst = obtener_nivel_15m(ticker, fecha_hoy)
        if nivel is not None and direccion_inst is not None:
            niveles[ticker] = nivel
            direcciones_inst[ticker] = direccion_inst
        else:
            print(f"· {ticker} excluido por falta de dirección institucional")

    activos_vivos = tickers_activos[:]
    print("\n🔁 Comenzando escaneo minuto a minuto\n", flush=True)

    hora_limite = datetime.strptime("10:01", "%H:%M").time()
    while activos_vivos and datetime.now(NY_TZ).time() < hora_limite:
        for ticker in activos_vivos[:]:
            try:
                fin = datetime.now(NY_TZ)
                inicio = fin - timedelta(minutes=3)
                inicio = NY_TZ.localize(inicio.replace(tzinfo=None))
                df = api.get_bars(ticker, "1Min", start=inicio.isoformat(), end=fin.isoformat()).df
                df = df.tz_convert("America/New_York")

                if len(df) < 3:
                    print(f"· {ticker} ➝ Datos insuficientes en 1Min — {len(df)} velas")
                    continue

                c1 = df["close"].iloc[-3]
                c2 = df["close"].iloc[-2]
                momento = df.index[-2].to_pydatetime()

                # 🧠 Recuperar nivel y dirección
                nivel = niveles.get(ticker)
                direccion_inst = direcciones_inst.get(ticker)
                if nivel is None or direccion_inst is None:
                    print(f"⚠️ {ticker} ➝ sin nivel o dirección institucional cargada")
                    continue

                print(f"· {ticker} ➝ Dirección: {direccion_inst}, Nivel: {nivel}, Cierres: {c1}, {c2}")

                if direccion_inst == "CALL" and c1 > nivel and c2 > nivel:
                    direccion = "CALL"
                elif direccion_inst == "PUT" and c1 < nivel and c2 < nivel:
                    direccion = "PUT"
                else:
                    print(f"· {ticker} ➝ Sin patrón — condiciones no cumplen nivel institucional")
                    continue

                print(f"\n📊 {ticker} ➝ Patrón {direccion} detectado — {momento.strftime('%H:%M')}", flush=True)
                                if confirmar_macd(ticker, momento, direccion):
                    try:
                        precio = round(c2, 2)
                        hora = momento.strftime("%H:%M")
                        mensaje = (
                            f"📡 *Señal institucional detectada*\n\n"
                            f"🔹 *Ticker:* `{ticker}`\n"
                            f"🔹 *Dirección:* `{direccion}`\n"
                            f"🔹 *Precio señal:* `${precio}`\n"
                            f"🔹 *MACD alineado:* `✅ {direccion} en múltiples marcos`\n"
                            f"🔹 *Nivel institucional:* `${nivel}`\n\n"
                            f"📊 *Diagnóstico técnico:*\n"
                            f"✔️ Confirmación por cuerpo de vela 15Min\n"
                            f"✔️ Doble cierre consecutivo sobre nivel\n"
                            f"✔️ Momentum multitimeframe validado\n\n"
                            f"🧭 *Oportunidad táctica intradía confirmada*"
                        )
                        enviar_mensaje(mensaje)

                        # 💼 Integración Vu Deja Contracts™ — selector de opciones
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

                        enviados.add(ticker)
                        activos_vivos.remove(ticker)
                        print(f"✅ Señal enviada para {ticker}\n", flush=True)

                    except Exception as e:
                        print(f"⚠️ Error al enviar mensaje para {ticker}: {e}", flush=True)
                else:
                    print("· Señal descartada — MACD insuficiente\n", flush=True)
            except Exception as e:
                print(f"⚠️ Error con {ticker}: {e}", flush=True)
        time.sleep(60)

    print("\n📋 Escaneo finalizado")
    print(f"📡 Tickers con señal: {list(enviados)}")
    print(f"🧭 Tickers sin señal: {list(set(tickers_activos) - enviados)}")
