#!/bin/bash
echo "======================================================"
echo " SHGLOBAL SOC - INSTALADOR CERO FRICCION (UBUNTU ISO)"
echo "======================================================"
echo ""
echo "[1/4] Actualizando repositorios e instalando bases..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv sqlite3

echo "[2/4] Aislado el entorno Python (VirtualEnv)..."
python3 -m venv venv
source venv/bin/activate

echo "[3/4] Descargando el cerebro de la Inteligencia Artificial y Motores Web..."
pip install fastapi uvicorn sqlalchemy pydantic requests

echo "[4/4] Inyectando el SOC como Demonios de Sistema (Tolerancia a Fallos)..."
# Servicio Web
sudo bash -c "cat > /etc/systemd/system/soc-backend.service" <<EOL
[Unit]
Description=ShGlobal SOC Backend (FastAPI SQL)
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

# Servicio Ingesta Syslog (Requiere Root por el puerto 514)
sudo bash -c "cat > /etc/systemd/system/soc-syslog.service" <<EOL
[Unit]
Description=ShGlobal SOC UDP 514 Syslog Receiver
After=network.target

[Service]
User=root
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python agents/syslog_receiver.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable soc-backend.service
sudo systemctl enable soc-syslog.service

echo ""
echo "======================================================"
echo "[OK] \u00a1INSTALACION COMPLETADA IMPECABLEMENTE!"
echo "Tu SOC ahora es nativo de este servidor Ubuntu."
echo ""
echo "COMANDOS DE ARRANQUE PARA PRODUCCION:"
echo "sudo systemctl start soc-backend"
echo "sudo systemctl start soc-syslog"
echo ""
echo "Tu tablero estara vivo 24/7 en: http://<IP_servidor>:8000"
echo "======================================================"
