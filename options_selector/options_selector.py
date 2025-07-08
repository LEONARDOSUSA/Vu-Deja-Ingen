from ib_insync import IB, Option, util
from datetime import datetime, timedelta

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)  # Gateway activo y TWS abierto

def get_expiration(ticker):
    today = datetime.now()
    if ticker == "SPY":
        return today.strftime('%Y-%m-%d')  # Vence hoy (0DTE)
    else:
        offset = (4 - today.weekday()) % 7  # 4 = viernes
        next_friday = today + timedelta(days=offset)
        return next_friday.strftime('%Y-%m-%d')

def buscar_opcion_ibkr(signal_data):
    ticker = signal_data["ticker"]
    direccion = signal_data["direccion"].upper()
    precio_referencia = signal_data["precio"]
    vencimiento = get_expiration(ticker)

    print(f"🔍 Buscando contrato óptimo: {ticker} | Dirección: {direccion} | Vencimiento: {vencimiento}")

    contratos_validos = []
    descartados = []

    strikes_referencia = [round(precio_referencia * x) for x in [0.95, 1.00, 1.05]]  # Rango táctico

    for strike in strikes_referencia:
        opcion = Option(ticker, vencimiento, strike, direccion.lower(), 'SMART')
        ib.qualifyContracts(opcion)
        market_data = ib.reqMktData(opcion, '', False, False)

        ib.sleep(1.2)  # Esperar datos

        bid = market_data.bid
        ask = market_data.ask
        last = market_data.last
        price = last if last else (bid + ask) / 2 if bid and ask else None
        spread = ask - bid if bid and ask else None
        volume = market_data.volume
        iv = market_data.impliedVolatility
        delta = getattr(market_data, 'modelGreeks', None).delta if market_data.modelGreeks else None

        # Verificar condiciones
        razones = []
        if price is None or not (0.80 <= price <= 1.50):
            razones.append("❌ Precio fuera de rango")
        if spread is None or spread > 0.40:
            razones.append("❌ Spread alto")
        if volume is None or volume < 350:
            razones.append("❌ Volumen insuficiente")
        if iv is None or iv > 0.60:
            razones.append("❌ IV elevada")
        if delta is None or abs(delta) < 0.18 * strike:
            razones.append("❌ Delta bajo")

        if not razones:
            contratos_validos.append({
                "symbol": f"{ticker} {vencimiento} {direccion} {strike}",
                "strike": strike,
                "expiration": vencimiento,
                "tipo": direccion,
                "delta": round(delta, 3),
                "precio": round(price, 2),
                "volume": volume,
                "iv": round(iv * 100, 2),
                "spread": round(spread, 2)
            })
        else:
            descartados.append({"strike": strike, "razones": razones})

        ib.cancelMktData(market_data)

    ib.disconnect()

    if contratos_validos:
        contrato_optimo = max(contratos_validos, key=lambda c: c["volume"] / (c["spread"] + 0.01))
        print(f"✅ Contrato óptimo encontrado: {contrato_optimo}")
        return contrato_optimo
    else:
        print("❌ No se encontró contrato con filtros tácticos")
        print("📋 Contratos descartados:")
        for d in descartados:
            print(f"Strike {d['strike']}: {', '.join(d['razones'])}")
        return None
