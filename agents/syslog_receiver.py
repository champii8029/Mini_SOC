import socket
import requests
from datetime import datetime
import re

# ==========================================
# RECEPTOR SYSLOG (100% PRODUCCI\u00d3N ISO 27001)
# ==========================================
# Este script escucha en el puerto UDP 514 para recibir trafico REAL del FortiGate
SOC_API_URL = "http://127.0.0.1:8000/api/logs"

def parse_syslog_to_soc(raw_msg, source_ip):
    # Extrae la informacion basica de un mensaje Syslog de Fortinet
    event_type = "FirewallLog"
    if "action=\"deny\"" in raw_msg or "action=\"blocked\"" in raw_msg:
        event_type = "TrafficBlock"
    elif "type=\"traffic\"" in raw_msg and "subtype=\"forward\"" in raw_msg:
        event_type = "ForwardTraffic"
    elif "type=\"traffic\"" in raw_msg and "subtype=\"local\"" in raw_msg:
        event_type = "LocalTraffic"
    
    # Intentar extraer SrcIP original del log en lugar de la IP del Firewall
    real_src_ip = source_ip
    match = re.search(r'srcip=([\d\.]+)', raw_msg)
    if match:
        real_src_ip = match.group(1)

    return {
        "source": "Fortinet_Syslog",
        "event_type": event_type,
        "source_ip": real_src_ip,
        "raw_log": raw_msg.strip()[:1000] # Truncar a 1000 chars m\u00e1x por seguridad en BD
    }

def start_syslog_server(host='0.0.0.0', port=514):
    print("====================================")
    print(" SOC SYSLOG RECEIVER (100% REAL)")
    print("====================================")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
        print(f"[*] Ingesta de Logs Aut\u00e9nticos escuchando en UDP {host}:{port}")
        print("[!] Tip: Configura tu FortiGate para enviar Logs Syslog a la IP de esta computadora en el puerto 514.")
        
        while True:
            data, addr = sock.recvfrom(4096)
            raw_msg = data.decode('utf-8', errors='ignore')
            
            # Formatear el crudo para la base de datos
            log_data = parse_syslog_to_soc(raw_msg, addr[0])
            
            # Enviar el log aut\u00e9ntico al backend del SOC (FastAPI)
            try:
                requests.post(SOC_API_URL, json=log_data, timeout=2)
                # print(f"Log real capturado y guardado: {log_data['event_type']} desde {addr[0]}")
            except Exception as e:
                print("[-] Error inyectando log real a la BD:", e)
                
    except PermissionError:
        print("[X] ERROR FATAL: No tienes permisos para abrir el puerto 514 (Syslog). Ejecuta esto como Administrador (o Root en Ubuntu).")
    except Exception as e:
        print(f"[X] FALLA EN SYSLOG SENSOR: {e}")

if __name__ == "__main__":
    start_syslog_server()
