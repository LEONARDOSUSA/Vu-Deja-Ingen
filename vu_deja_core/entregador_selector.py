from entregador_selector import generar_mensajes_por_nivel

signal_data = {"ticker": "SPY", "direccion": "CALL"}
nivel_cliente = "intermedio"
client_id = 1002

mensajes = generar_mensajes_por_nivel(signal_data, nivel_cliente, client_id)

for msg in mensajes:
    print(msg)  # 🖥️ Terminal
    enviar_mensaje_telegram(msg, chat_id)  # 📲 Telegram, si lo tenés conectado
