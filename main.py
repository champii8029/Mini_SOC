from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import logs, alerts, metrics
import os

# Crear el directorio base si no existe
os.makedirs("static", exist_ok=True)

# Inicializar DB: esto crea el archivo soc.db y sus tablas autom\u00e1ticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini SOC API", description="API central para el SOC interno", version="1.0.0")

# Intercambio de Recursos de Origen Cruzado (CORS)
# Muy importante para que nuestro frontend en HTML/JS simple pueda consultarlo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integrar Rutas
from routers import firewall

app.include_router(logs.router, prefix="/api", tags=["Logs"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(metrics.router)
app.include_router(firewall.router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    # Inicia el motor de la API local
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
