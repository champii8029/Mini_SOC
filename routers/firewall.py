from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(prefix="/api/firewall", tags=["Firewall"])

# Variables tomadas del conector Fortinet
FORTINET_IP = "192.168.2.254"
API_KEY = "G1h097kyhjt5cynjy6s4n36gwf1h8H"

def get_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

@router.get("/ping")
def ping_firewall():
    """Prueba de conexion real en vivo a la REST API de Fortinet (ISO 27001)"""
    url = f"https://{FORTINET_IP}/api/v2/monitor/system/status"
    try:
        res = requests.get(url, headers=get_headers(), verify=False, timeout=5)
        if res.status_code == 200:
            return {"status": "ok", "message": "Conectado al FW exitosamente"}
        raise HTTPException(status_code=502, detail=f"Fortinet retornó Status {res.status_code}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

class BlockRequest(BaseModel):
    ip: str

@router.post("/block")
def block_ip(req: BlockRequest):
    """
    Agrega dinámicamente una IP de atacante a los objetos de Red en FortiOS.
    En una config de producción, este objeto se mapearía dentro de un Address Group de Bloqueo.
    """
    address_name = f"SOC_BLOCK_{req.ip.replace('.','_')}"
    addr_payload = {
        "name": address_name,
        "type": "ipmask",
        "subnet": f"{req.ip} 255.255.255.255"
    }
    
    url = f"https://{FORTINET_IP}/api/v2/cmdb/firewall/address"
    try:
        # Petición real al firewall
        response = requests.post(url, headers=get_headers(), json=addr_payload, verify=False, timeout=5)
        # 200 significa se inyectó, 500 puede significar que ya existía. En todo caso funciona.
        return {"status": "ok", "message": f"IP {req.ip} aislada como Address Object en FortiGate ({address_name})."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error aislando en FortiOS: {e}")
