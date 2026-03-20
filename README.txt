================================================================================
         ShGlobal SOC - Centro de Operaciones de Seguridad v1.0
               Sistema de Monitoreo de Ciberseguridad ISO 27001
================================================================================

Autor:         [Jose de Jesus Torres Saucedo]
Correo:        [champii.sc@gmail.com]
LinkedIn:      [www.linkedin.com/in/jose-de-jesus-torres-saucedo-2935a5a3]
GitHub:        [https://github.com/champii8029]
Fecha:         Marzo 2026

================================================================================
                          DESCRIPCION DEL PROYECTO
================================================================================

Mini SOC (Security Operations Center) es un sistema completo y gratuito de
monitoreo de ciberseguridad en tiempo real, disenado para empresas pequenas
y medianas que buscan cumplir con estandares como ISO 27001 y TISAX sin
necesidad de pagar licencias costosas como Splunk o QRadar.

Funcionalidades principales:
  - Dashboard ejecutivo con metricas en tiempo real
  - Ingesta nativa de logs via Syslog (UDP 514) desde Fortinet
  - Motor SOAR con acciones automatizadas (bloqueo de IP, cierre de alertas)
  - Escaner de red automatico (descubrimiento de activos)
  - Alertas y heartbeat via Telegram Bot
  - Exportacion de reportes en CSV/PDF
  - Graficas de ataques y puertos mas vulnerados

================================================================================
                             REQUISITOS PREVIOS
================================================================================

Hardware:
  - Servidor o maquina virtual con Ubuntu 20.04 o superior
  - Minimo 2 GB de RAM y 20 GB de disco
  - Conexion a la red local (IP estatica recomendada)

Software:
  - Python 3.10 o superior
  - pip3 (gestor de paquetes de Python)
  - SQLite3 (base de datos ligera)
  - Navegador web moderno (Chrome, Firefox, Edge)

Red:
  - Firewall Fortinet con acceso a la interfaz web de administracion
  - Puerto UDP 514 abierto en el servidor para recibir Syslog
  - Puerto TCP 8000 abierto para acceder al Dashboard desde la red

Telegram (Opcional):
  - Crear un Bot en Telegram buscando @BotFather
  - Obtener el Token del Bot y el Chat ID de tu grupo/canal

================================================================================
                     PASO 1: PREPARAR EL SERVIDOR UBUNTU
================================================================================

1.1  Abrir la Terminal en Ubuntu (Ctrl+Alt+T)

1.2  Actualizar el sistema operativo:
     $ sudo apt-get update

     NOTA: Si falla diciendo que no encuentra las ligas, el servidor
     probablemente no tiene DNS configurado. Arreglalo con:
     $ echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null
     Despues repite el apt-get update.

1.3  Instalar Python y herramientas base:
     $ sudo apt-get install -y python3 python3-pip python3-venv sqlite3

1.4  Verificar que Python se instalo correctamente:
     $ python3 --version
     Debe responder algo como: Python 3.10.12

================================================================================
                     PASO 2: COPIAR LOS ARCHIVOS DEL PROYECTO
================================================================================

2.1  Copiar la carpeta completa "mini_soc" al servidor Ubuntu.
     Puedes usar una memoria USB, WinSCP, FileZilla o cualquier metodo.

2.2  Colocar la carpeta en una ubicacion comoda, por ejemplo:
     /home/tu-usuario/Descargas/mini_soc

2.3  Abrir la terminal y navegar a la carpeta:
     $ cd ~/Descargas/mini_soc

================================================================================
                     PASO 3: CONFIGURAR VARIABLES DE ENTORNO
================================================================================

3.1  Crear el archivo de configuracion ".env" dentro de la carpeta mini_soc:
     $ nano .env

3.2  Escribir las siguientes variables (reemplaza con tus datos reales):

     TELEGRAM_BOT_TOKEN=tu-token-del-bot-aqui
     TELEGRAM_CHAT_ID=tu-chat-id-aqui
     FORTINET_IP=la-ip-de-tu-fortigate
     API_KEY=tu-api-key-de-fortinet
     SOC_API_URL=http://127.0.0.1:8000/api/logs

3.3  Guardar con Ctrl+O, Enter, y salir con Ctrl+X.

     IMPORTANTE: Este archivo contiene credenciales sensibles.
     NUNCA lo compartas ni lo subas a GitHub.

================================================================================
                     PASO 4: INSTALAR DEPENDENCIAS DE PYTHON
================================================================================

4.1  Crear un entorno virtual aislado:
     $ python3 -m venv venv

4.2  Activar el entorno virtual:
     $ source venv/bin/activate

4.3  Instalar las librerias necesarias:
     $ pip install fastapi uvicorn sqlalchemy pydantic requests

================================================================================
                     PASO 5: CONVERSION DE ARCHIVOS (IMPORTANTE)
================================================================================

     Si copiaste los archivos desde una computadora con Windows, es necesario
     convertir los saltos de linea al formato de Linux:

5.1  Instalar el convertidor:
     $ sudo apt-get install -y dos2unix

5.2  Convertir los archivos criticos:
     $ dos2unix install_soc.sh
     $ dos2unix fix_appjs.sh

================================================================================
                     PASO 6: INSTALACION AUTOMATICA (CON SUDO)
================================================================================

     Si tienes permisos de superusuario (sudo), puedes usar el instalador
     automatico que crea demonios de sistema (servicios que arrancan solos):

     $ sudo bash install_soc.sh

     Esto creara dos servicios de systemd:
       - soc-backend.service  (Servidor Web FastAPI en puerto 8000)
       - soc-syslog.service   (Receptor de logs Fortinet en puerto UDP 514)

     Verificar que esten activos:
     $ sudo systemctl status soc-backend
     $ sudo systemctl status soc-syslog

     Ambos deben mostrar "active (running)" en color verde.

================================================================================
                     PASO 6 (ALTERNATIVA): SIN PERMISOS SUDO
================================================================================

     Si NO tienes permisos de superusuario, puedes ejecutar todo manualmente:

     $ source venv/bin/activate
     $ nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
     $ nohup python3 agents/syslog_receiver.py > syslog.log 2>&1 &
     $ nohup python3 agents/network_scanner.py > scanner.log 2>&1 &
     $ nohup python3 agents/soc_heartbeat.py > heartbeat.log 2>&1 &

     NOTA: Si el servidor se reinicia, deberas ejecutar estos comandos de nuevo.

================================================================================
                     PASO 7: CONFIGURAR FORTINET (SYSLOG)
================================================================================

7.1  Entrar al panel web del FortiGate (https://ip-de-tu-fortigate)

7.2  Ir a: Log & Report > Log Settings

7.3  En la seccion "Remote Logging and Archiving":
     - Activar "Send logs to Syslog"
     - IP/FQDN: Colocar la IP de tu servidor Ubuntu (ej: 192.168.2.250)
     - Puerto: 514

7.4  Ir a: Policy & Objects > Firewall Policy (o IPv4 Policy)
     - Abrir la politica principal de navegacion (ej: "LAN to WAN")
     - Bajar hasta "Logging Options"
     - Activar "Log Allowed Traffic" y seleccionar "All Sessions"
     - Guardar con OK

================================================================================
                     PASO 8: ACCEDER AL DASHBOARD
================================================================================

8.1  Desde la MISMA maquina Ubuntu:
     Abrir Firefox y navegar a:  http://localhost:8000/static/index.html

8.2  Desde OTRA computadora en la misma red:
     Abrir Chrome y navegar a:  http://IP-DEL-UBUNTU:8000/static/index.html
     Ejemplo: http://192.168.2.250:8000/static/index.html

     NOTA: Si la pagina carga pero los datos aparecen en cero, limpia
     el cache del navegador con Ctrl+Shift+F5 o abre una ventana de
     Incognito (Ctrl+Shift+N).

================================================================================
                     PASO 9: VERIFICAR TELEGRAM (OPCIONAL)
================================================================================

9.1  Si configuraste el Bot de Telegram en el archivo .env, el sistema
     enviara un mensaje de "Heartbeat" periodicamente confirmando que
     el SOC esta operativo.

9.2  Si no recibes mensajes, verifica el log del heartbeat:
     $ cat heartbeat.log

================================================================================
                          SOLUCION DE PROBLEMAS
================================================================================

PROBLEMA: "python3: command not found"
SOLUCION: Instalar Python con:
  $ sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv

PROBLEMA: "apt-get: Failed to fetch" o "No se localizo el paquete"
SOLUCION: El servidor no tiene DNS. Arreglalo con:
  $ echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null
  $ sudo apt-get update

PROBLEMA: "bad interpreter: /bin/bash^M"
SOLUCION: Los archivos tienen formato Windows. Convertir con:
  $ sudo apt-get install dos2unix && dos2unix install_soc.sh

PROBLEMA: "inactive (dead)" al revisar el servicio con systemctl
SOLUCION: Revisar el error real con:
  $ ./venv/bin/python3 main.py
  Corregir el error que muestre y reiniciar con:
  $ sudo systemctl daemon-reload && sudo systemctl restart soc-backend

PROBLEMA: Dashboard carga pero los datos aparecen en cero (remoto)
SOLUCION: Limpiar cache del navegador (Ctrl+Shift+F5) o usar Incognito.
  Verificar que la primera linea de static/app.js diga:
  const API_URL = window.location.origin + "/api";

PROBLEMA: No llegan mensajes de Telegram
SOLUCION: Verificar que el archivo .env tenga el Token y Chat ID correctos.
  Reiniciar el agente:
  $ pkill -f soc_heartbeat && nohup python3 agents/soc_heartbeat.py > heartbeat.log 2>&1 &

================================================================================
                          ESTRUCTURA DEL PROYECTO
================================================================================

mini_soc/
  main.py                  - Punto de entrada del servidor FastAPI
  database.py              - Configuracion de la base de datos SQLite
  models.py                - Modelos de datos (LogEvent, Alert)
  schemas.py               - Esquemas de validacion Pydantic
  .env                     - Variables de entorno (NUNCA SUBIR A GITHUB)
  .gitignore               - Archivos excluidos de Git
  install_soc.sh           - Instalador automatico para Ubuntu
  fix_appjs.sh             - Reparador del archivo JavaScript
  soc.db                   - Base de datos SQLite (se crea automaticamente)
  routers/
    logs.py                - Endpoints de ingesta de logs
    alerts.py              - Endpoints de gestion de alertas
    metrics.py             - Endpoints de metricas y dashboards
    firewall.py            - Endpoints de integracion con Fortinet
  agents/
    syslog_receiver.py     - Receptor nativo de Syslog UDP (puerto 514)
    network_scanner.py     - Escaner automatico de red
    soc_heartbeat.py       - Bot de Telegram para monitoreo
  services/
    analyzer.py            - Motor de deteccion de amenazas
  static/
    index.html             - Interfaz grafica del Dashboard
    styles.css             - Estilos visuales (tema claro corporativo)
    app.js                 - Logica JavaScript del frontend

================================================================================
                              LICENCIA
================================================================================

Este proyecto es de codigo abierto. Puedes usarlo, modificarlo y distribuirlo
libremente. Si te fue util, considera dar credito al autor original.

================================================================================
                       Desarrollado con pasion por
                   [TU NOMBRE] - Ciberseguridad ShGlobal
                              Marzo 2026
================================================================================
