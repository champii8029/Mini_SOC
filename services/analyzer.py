from sqlalchemy.orm import Session
from models import LogEvent, Alert
from datetime import datetime, timedelta
import requests

# ==========================================
# CONFIGURACI\u00d3N DE NOTIFICACIONES TELEGRAM
# ==========================================
TELEGRAM_BOT_TOKEN = "8749350265:AAFnd87ipyfLJwOd4H7iXKIUVbNjLPpDyTY"
TELEGRAM_CHAT_ID = "925654613"

def send_telegram_alert(title, description):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "PUN_TU_TOKEN_AQUI":
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"\ud83d\udea8 ALERTA CRITICA SOC \ud83d\udea8\n\n\ud83d\udccc {title}\n\ud83d\udcdd {description}\n\n\ud83d\udd0d Ingresa al ShGlobal Dashboard de inmediato."
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"[TG] Notificaci\u00f3n Push Status: {res.status_code}")
    except Exception as e:
        print(f"[TG] Error PUSH: {e}")

def analyze_log(db: Session, newly_inserted_log: LogEvent):
    """
    Motor de reglas simple. Eval\u00faa un nuevo log para ver si dispara alertas.
    Esta l\u00f3gica est\u00e1 pensada para Windows Servers y Fortinet Firewalls.
    """
    now = datetime.utcnow()
    
    # REGLA 1: WINDOWS - Ataque de Fuerza Bruta
    # 5 intentos de login fallidos en los \u00faltimos 5 minutos desde la misma IP.
    if newly_inserted_log.event_type == "WindowsLoginFailed" and newly_inserted_log.source_ip:
        time_threshold = now - timedelta(minutes=5)
        failed_count = db.query(LogEvent).filter(
            LogEvent.event_type == "WindowsLoginFailed",
            LogEvent.source_ip == newly_inserted_log.source_ip,
            LogEvent.timestamp >= time_threshold
        ).count()
        
        if failed_count >= 5:
            # Revisa si ya lanzamos una alerta parecida hace poco para no hacer spam (ruido al SOC)
            recent_alert = db.query(Alert).filter(
                Alert.title == "Posible Ataque de Fuerza Bruta (Windows)",
                Alert.description.like(f"%{newly_inserted_log.source_ip}%"),
                Alert.timestamp >= time_threshold
            ).first()
            
            if not recent_alert:
                alert = Alert(
                    title="Posible Ataque de Fuerza Bruta (Windows)",
                    severity="High",
                    description=f"Se detectaron {failed_count} logins fallidos repititivos (ID 4625) desde la IP {newly_inserted_log.source_ip} en los \u00faltimos 5 minutos."
                )
                db.add(alert)
                db.commit()
                send_telegram_alert(alert.title, alert.description)

    # REGLA 2: FORTINET - Detecci\u00f3n de Malware o Intruso (IPS/AV)
    if newly_inserted_log.source == "Fortinet" and "msg=\"File is infected\"" in newly_inserted_log.raw_log:
        alert = Alert(
            title="Detecci\u00f3n de Malware en Fortinet",
            severity="Critical",
            description=f"El firewall report\u00f3 un archivo malicioso bloqueado. IP Origen: {newly_inserted_log.source_ip}. Log original: {newly_inserted_log.raw_log}"
        )
        db.add(alert)
        db.commit()
        send_telegram_alert(alert.title, alert.description)

    # REGLA 3: FORTINET - Denegaci\u00f3n de tr\u00e1fico extra\u00f1a (escaneo de puertos)
    if newly_inserted_log.source == "Fortinet" and newly_inserted_log.event_type == "TrafficBlock" and newly_inserted_log.source_ip:
        time_threshold = now - timedelta(minutes=1)
        blocked_count = db.query(LogEvent).filter(
            LogEvent.source == "Fortinet",
            LogEvent.event_type == "TrafficBlock",
            LogEvent.source_ip == newly_inserted_log.source_ip,
            LogEvent.timestamp >= time_threshold
        ).count()

        if blocked_count >= 50:
            recent_alert = db.query(Alert).filter(
                Alert.title == "Posible Escaneo de Puertos bloqueado por Firewall",
                Alert.description.like(f"%{newly_inserted_log.source_ip}%"),
                Alert.timestamp >= time_threshold
            ).first()
            
            if not recent_alert:
                alert = Alert(
                    title="Posible Escaneo de Puertos bloqueado por Firewall",
                    severity="Medium",
                    description=f"El Fortinet ha bloqueado mas de 50 flujos de conexi\u00f3n desde la IP {newly_inserted_log.source_ip} en solo 1 minuto."
                )
                db.add(alert)
                db.commit()
