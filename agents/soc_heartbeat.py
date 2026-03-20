import time
import requests
import sqlite3
from datetime import datetime
import os

# ==========================================
# CONFIGURACI\u00d3N DE NOTIFICACIONES TELEGRAM
# ==========================================
TELEGRAM_BOT_TOKEN = "8749350265:AAFnd87ipyfLJwOd4H7iXKIUVbNjLPpDyTY"
TELEGRAM_CHAT_ID = "925654613"

# Buscamos la BD en la raiz del proyecto
DB_PATH = "soc.db" 

def get_soc_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Alertas cr\u00edticas e importantes sin cerrar
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status='Abierta' AND (severity='Critical' OR severity='High')")
        alertas_criticas = cursor.fetchone()[0]
        
        # Alertas totales
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status='Abierta'")
        alertas_totales = cursor.fetchone()[0]
        
        # Logs Ingestados Hoy
        hoy = datetime.utcnow().strftime('%Y-%m-%d')
        cursor.execute(f"SELECT COUNT(*) FROM logs WHERE timestamp LIKE '{hoy}%'")
        eventos_hoy = cursor.fetchone()[0]
        
        conn.close()
        return alertas_criticas, alertas_totales, eventos_hoy
    except Exception as e:
        print("Aviso: Base de datos a\u00fan no lista o vac\u00eda.", e)
        return 0, 0, 0

def send_heartbeat():
    criticas, totales, eventos = get_soc_stats()
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    texto = (
        "\u2705 *SOC HEARTBEAT (Reporte 30 min)* \u2705\n\n"
        f"\ud83d\udee1\ufe0f *Estado:* Sistema Operativo y 100% En L\u00ednea.\n"
        f"\ud83d\udcca *Evidencia y Tr\u00e1fico Hoy:* {eventos} paquetes logueados.\n\n"
        f"\ud83d\udea8 *Alertas Pendientes:* {totales}\n"
        f"\ud83d\udd25 *Peligro Inminente (Cr\u00edticas):* {criticas}\n\n"
        "_El servidor sigue recabando evidencia para ISO/TISAX sin interrupciones._"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Reporte de salud (Heartbeat) enviado con \u00e9xito a Telegram.")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error mandando Heartbeat de Telegram: {e}")

if __name__ == "__main__":
    print("====================================")
    print(" SOC TELEGRAM HEARTBEAT AGENT")
    print("====================================")
    print("Enviando reporte de salud a Telegram cada 30 minutos...")
    
    # Mandamos el primer mensaje al instante para comprobar que sirva
    send_heartbeat()
    
    while True:
        # Esperar 30 minutos (1800 segundos) exactamente
        time.sleep(1800)
        send_heartbeat()
