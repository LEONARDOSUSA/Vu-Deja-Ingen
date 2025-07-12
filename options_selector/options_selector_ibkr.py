from ib_insync import IB, Option, Stock
from datetime import datetime, timedelta

# 🔌 Conexión a IBKR
def conectar_ibkr(client_id=1):
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=client_id)
    return ib

# 📦 Consultar precio spot en tiempo real
def obtener_precio_spot_ibkr(ticker):
    ib = conectar_ibkr(client_id=999)  # clientId exclusivo para spot
    contrato = Stock(ticker.upper(), 'SMART', 'USD')
    ib.qualifyContracts(contrato)
    md = ib.reqMktData(contrato, '', False, False)
    ib.sleep(1.5)
    spot = md.last or md.close or ((md.bid + md.ask) / 2)
    ib.cancelMktData(md)
    ib.disconnect()
    return round(spot, 2)

# 📅 Vencimiento dinámico
def get_expiration(ticker):
    today = datetime.now()
    if ticker.upper() == "SPY":
        return today.strftime('%Y-%m-%d')  # Vencimiento diario
    else:
        offset = (4 - today.weekday()) % 7
        next_friday = today + timedelta(days=offset)
        return next_friday.strftime('%Y-%m-%d')

# 🧠 Escanear contratos reales
def obtener_contratos_ibkr(signal_data, client_id=1):
    ticker = signal_data["ticker"].upper()
    direccion = signal_data["direccion"].upper()
    spot_price = obtener_precio_spot_ibkr(ticker)
    vencimiento = get_expiration(ticker)

    ib = conectar_ibkr(client_id)
    print(f"🔍 {ticker} | Dirección: {direccion} | Spot: {spot_price} | Vencimiento: {vencimiento}")

    contratos_validos = []
    strikes_referencia = [round(spot_price * x) for x in [0.95, 1.00, 1.05]]

    for strike in strikes_referencia:
        opcion = Option(ticker, vencimiento, strike, direccion.lower(), 'SMART')
        ib.qualifyContracts(opcion)
        market_data = ib.reqMktData(opcion, '', False, False)
        ib.sleep(1.5)

        bid = market_data.bid
        ask = market_data.ask
        last = market_data.last
        price = last or ((bid + ask) / 2 if bid and ask else None)
        spread = ask - bid if bid and ask else None
        volume = market_data.volume
        iv = market_data.impliedVolatility
        delta = market_data.modelGreeks.delta if market_data.modelGreeks else None

        contrato = {
            "symbol": f"{ticker} {vencimiento} {direccion} {strike}",
            "strike": strike,
            "expiration": vencimiento,
            "tipo": direccion,
            "delta": round(delta, 3) if delta else None,
            "precio": round(price, 2) if price else None,
            "volume": volume,
            "iv": round(iv * 100, 2) if iv else None,
            "spread": round(spread, 2) if spread else None
        }

        if (
            contrato["precio"] and 0.8 <= contrato["precio"] <= 2.0 and
            contrato["spread"] and contrato["spread"] <= 0.25 and
            contrato["volume"] and contrato["volume"] > 200 and
            contrato["iv"] and 35 <= contrato["iv"] <= 60 and
            contrato["delta"] and abs(contrato["delta"]) >= 0.2
        ):
            contratos_validos.append(contrato)

        ib.cancelMktData(market_data)

    ib.disconnect()

    def score(c):
        return c["delta"] + (c["volume"] * 0.0001) - c["spread"]

    return sorted(contratos_validos, key=score, reverse=True)

# 👤 Asignar contrato institucional por cliente
def asignar_contrato_ibkr(signal_data, cliente_id):
    contratos = obtener_contratos_ibkr(signal_data, client_id=cliente_id)
    if not contratos:
        return {"error": "❌ No hay contratos válidos para esta señal con IBKR."}
    index = cliente_id % len(contratos)
    return contratos[index]

# 🧪 Test local institucional
if __name__ == "__main__":
    señal = {"ticker": "SPY", "direccion": "CALL"}
    contratos = obtener_contratos_ibkr(señal)

    for idx, contrato in enumerate(contratos, start=1):
        print(f"\n⚡ Contrato #{idx}: {contrato['symbol']}")
        print(f"📅 Vencimiento: {contrato['expiration']} | Strike: {contrato['strike']}")
        print(f"📊 Delta: {contrato['delta']} | IV: {contrato['iv']} | Volumen: {contrato['volume']}")
        print(f"💸 Spread: {contrato['spread']} | Precio: {contrato['precio']}")
