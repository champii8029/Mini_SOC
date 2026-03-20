from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class LogEvent(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True) # ej., 'Fortinet', 'WindowsServer01'
    event_type = Column(String, index=True) # ej., 'LoginFailed', 'TrafficBlock'
    source_ip = Column(String, index=True, nullable=True)
    raw_log = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    severity = Column(String) # 'High', 'Medium', 'Low', 'Critical'
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default="Abierta") # 'Abierta', 'En Investigaci\u00f3n', 'Cerrada'
