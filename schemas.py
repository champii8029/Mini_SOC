from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LogCreate(BaseModel):
    source: str
    event_type: str
    source_ip: Optional[str] = None
    raw_log: str

class LogResponse(LogCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True  # Pydantic v2 support para ORM objects

class AlertResponse(BaseModel):
    id: int
    title: str
    severity: str
    description: str
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True
