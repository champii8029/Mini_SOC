from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from services.analyzer import analyze_log

router = APIRouter()

@router.post("/logs", response_model=schemas.LogResponse)
def create_log(log: schemas.LogCreate, db: Session = Depends(get_db)):
    # 1. Crear el log en la BD instanciando el modelo
    db_log = models.LogEvent(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log) # Refrescar para obtener el ID y Timestamp generado
    
    # 2. Analizar el log autom\u00e1ticamente contra las reglas del SOC
    analyze_log(db, db_log)
    
    return db_log

@router.get("/logs", response_model=list[schemas.LogResponse])
def get_logs(db: Session = Depends(get_db), limit: int = 100):
    # Retornar los logs m\u00e1s recientes primero
    return db.query(models.LogEvent).order_by(models.LogEvent.timestamp.desc()).limit(limit).all()

@router.get("/logs/forward", response_model=list[schemas.LogResponse])
def get_forward_logs(db: Session = Depends(get_db), limit: int = 150):
    return db.query(models.LogEvent).filter(models.LogEvent.event_type == 'ForwardTraffic').order_by(models.LogEvent.timestamp.desc()).limit(limit).all()
