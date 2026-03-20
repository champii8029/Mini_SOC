from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import database
import models
import re
from collections import Counter

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(database.get_db)):
    # 1. Top 5 IPs Hostiles (IPs que no sean locales)
    top_ips_query = db.query(models.LogEvent.source_ip, func.count(models.LogEvent.id).label('count')) \
        .filter(models.LogEvent.source_ip != None) \
        .filter(models.LogEvent.source_ip != '') \
        .filter(models.LogEvent.source_ip.notlike('192.168.%')) \
        .filter(models.LogEvent.source_ip.notlike('127.%')) \
        .group_by(models.LogEvent.source_ip) \
        .order_by(func.count(models.LogEvent.id).desc()) \
        .limit(5).all()

    top_ips_labels = [row[0] for row in top_ips_query]
    top_ips_data = [row[1] for row in top_ips_query]

    if not top_ips_labels:
        top_ips_labels = ["Sin Ataques Registrados"]
        top_ips_data = [0]

    # 2. Top 5 Puertos Analizando el Texto Crudo (dstport=XXX)
    fortinet_logs = db.query(models.LogEvent.raw_log).filter(models.LogEvent.source == 'Fortinet').all()
    port_counter = Counter()
    
    port_regex = re.compile(r'dstport=(\d+)')
    for log in fortinet_logs:
        if log[0]: # If raw_log is not none
            match = port_regex.search(log[0])
            if match:
                port_counter[match.group(1)] += 1
                
    top_ports_labels = []
    top_ports_data = []
    
    if port_counter:
        for port, count in port_counter.most_common(5):
            port_name = f"Port {port}"
            if port == '443': port_name = 'HTTPS (443)'
            elif port == '80': port_name = 'HTTP (80)'
            elif port == '22': port_name = 'SSH (22)'
            elif port == '3389': port_name = 'RDP (3389)'
            elif port == '445': port_name = 'SMB (445)'
            elif port == '53': port_name = 'DNS (53)'
            top_ports_labels.append(port_name)
            top_ports_data.append(count)
    else:
        top_ports_labels = ["Sin tráfico bloqueado"]
        top_ports_data = [0]

    return {
        "top_ips": {"labels": top_ips_labels, "data": top_ips_data},
        "top_ports": {"labels": top_ports_labels, "data": top_ports_data}
    }

@router.get("/hosts")
def get_discovered_hosts(db: Session = Depends(database.get_db)):
    """
    Retorna la lista de hosts y su Hostname (extraído del raw_log) descubiertas por el scanner.
    """
    all_hosts_logs = db.query(models.LogEvent)\
        .filter(models.LogEvent.event_type == 'HostDiscovery')\
        .order_by(models.LogEvent.timestamp.desc())\
        .all()
    
    unique_hosts = {}
    for log in all_hosts_logs:
        if log.source_ip and log.source_ip not in unique_hosts:
            hostname = "Desconocido"
            if log.raw_log and "Hostname:" in log.raw_log:
                parts = log.raw_log.split("Hostname:")
                if len(parts) > 1:
                    hostname = parts[1].strip()
                    
            unique_hosts[log.source_ip] = {
                "ip": log.source_ip,
                "hostname": hostname,
                "last_seen": log.timestamp.strftime("%I:%M:%S %p") if log.timestamp else "Desconocido"
            }
    return list(unique_hosts.values())

import socket

@router.get("/scan_ports/{ip}")
def scan_critical_ports(ip: str):
    """
    Escanea bajo demanda los puertos m\u00e1s cr\u00edticos de una IP espec\u00edfica usando sockets nativos de Python.
    """
    critical_ports = {
        22: "SSH",
        80: "HTTP",
        443: "HTTPS",
        445: "SMB",
        3389: "RDP",
        3306: "MySQL"
    }
    open_ports = []
    
    for port, name in critical_ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5) # Timeout extremadamente bajo (500ms) para que responda instant\u00e1neo al Dashboard
        result = sock.connect_ex((ip, port))
        if result == 0:
            open_ports.append(f"{port} ({name})")
        sock.close()
        
    return {"ip": ip, "open_ports": open_ports}

from fastapi.responses import PlainTextResponse

@router.get("/export_csv")
def export_hosts_csv(db: Session = Depends(database.get_db)):
    """Genera CSV en demanda del inventario para auditorias ISO 27001"""
    hosts_logs = db.query(models.LogEvent).filter(models.LogEvent.event_type == 'HostDiscovery').order_by(models.LogEvent.timestamp.desc()).all()
    unique = {}
    for log in hosts_logs:
        if log.source_ip and log.source_ip not in unique:
            h = "Desconocido"
            if log.raw_log and "Hostname:" in log.raw_log:
                pts = log.raw_log.split("Hostname:")
                if len(pts) > 1: h = pts[1].strip()
            unique[log.source_ip] = f"{log.source_ip},{h},{log.timestamp}"
            
    csv_str = "IP,Hostname,Ultima Vez Visto\n"
    for line in unique.values():
        csv_str += f"{line}\n"
        
    return PlainTextResponse(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inventario_activos.csv"})

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(database.get_db)):
    from datetime import timedelta
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    total_logs = db.query(models.LogEvent).filter(models.LogEvent.timestamp >= one_hour_ago).count()
    activos = db.query(models.LogEvent.source_ip).filter(models.LogEvent.event_type == 'HostDiscovery').distinct().count()
    alertas_activas = db.query(models.Alert).filter(models.Alert.status == 'Abierta').filter(models.Alert.severity.in_(['Critical', 'High'])).count()
    
    return {
        "eventos_hoy": total_logs or 0,
        "activos_vigilados": activos or 0,
        "alertas_criticas": alertas_activas or 0
    }
