import os
import platform
import subprocess
import concurrent.futures
import ipaddress
import requests

SOC_API_URL = "http://localhost:8000/api/logs"

# Los segmentos reales de la empresa
SUBNETS = [
    "192.168.0.0/24",
    "192.168.1.0/24",
    "192.168.2.0/24",
    "192.168.3.0/24",
    "192.168.4.0/24"
]

def ping_ip(ip):
    """Hace ping a una IP y devuelve la IP si est\u00e1 activa."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    # Solo 1 paquete, timeout de 800ms para ser r\u00e1pidos pero precisos
    command = ['ping', param, '1', '-w', '800', str(ip)]
    
    resultado = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if resultado == 0:
        return str(ip)
    return None

def scan_network():
    print("====================================")
    print(" SOC NETWORK SCANNER INIT")
    print("====================================")
    print("Trazando el mapa de red interno...")
    active_hosts = []
    
    all_ips = []
    for subnet in SUBNETS:
        network = ipaddress.ip_network(subnet, strict=False)
        for ip in network.hosts(): # .hosts() ignora la .0 y la .255
            all_ips.append(ip)
            
    print(f"Total de IPs a escanear: {len(all_ips)} (Esto tomar\u00e1 s\u00f3lo unos segundos)\n")
    
    # 100 hilos paralelos para escanear todo el /24 rapid\u00edsimo
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        resultados = executor.map(ping_ip, all_ips)
        
        for ip in resultados:
            if ip:
                active_hosts.append(ip)
                
                # Intentar resolver el Nombre del Dispositivo (Hostname)
                import socket
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    hostname = "Desconocido"

                print(f"[+] Equipo Activo Descubierto: {ip} ({hostname})")
                
                # Enviamos el descubrimiento al SOC de forma silenciosa
                log_data = {
                    "source": "NetworkScanner",
                    "event_type": "HostDiscovery",
                    "source_ip": ip,
                    "raw_log": f"Hostname: {hostname}"
                }
                try:
                    requests.post(SOC_API_URL, json=log_data)
                except:
                    pass # Si el SOC est\u00e1 apagado, ignora el error
                
    print(f"\n>>> Escaneo terminado. {len(active_hosts)} equipos activos encontrados en la red.")

if __name__ == "__main__":
    import time
    while True:
        try:
            scan_network()
        except Exception as e:
            print(f"Error en el escaneo: {e}")
            
        print("\n⏳ Esperando 5 minutos para el siguiente escaneo (Auto-Actualización)...")
        time.sleep(300)
