from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from typing import Optional

router = APIRouter()

@router.get("/alerts", response_model=list[schemas.AlertResponse])
def get_alerts(db: Session = Depends(get_db), limit: int = 50):
    return db.query(models.Alert).order_by(models.Alert.timestamp.desc()).limit(limit).all()

@router.put("/alerts/{alert_id}/status")
def update_alert_status(alert_id: int, status: str, note: Optional[str] = None, db: Session = Depends(get_db)):
    """ISO 27001 Incident Log Trail appending"""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if alert:
        alert.status = status
        if note:
            alert.description = f"{alert.description}\n\n[RESOLUCIÓN SOC]: {note}"
        db.commit()
        return {"msg": f"El estado de la alerta {alert_id} fué actualizado a '{status}'."}
    return {"msg": "Alerta no encontrada", "error": True}
