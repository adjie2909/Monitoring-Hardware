from database import Base, engine
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship

class Hardware(Base):
    __tablename__ = "hardware"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_tag = Column(String(50), unique=True, nullable=False)
    device_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    ip_address = Column(String(45))
    purchase_date = Column(DateTime)
    status = Column(String(20), default="Active")
    serial_number = Column(String(100), unique=True, nullable=True)

    maintenance_logs = relationship("MaintenanceLog", back_populates="hardware", cascade="all, delete-orphan")


class MaintenanceLog(Base):
    __tablename__ = "maintenance_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hardware_id = Column(Integer, ForeignKey("hardware.id"), nullable=False)
    maintenance_type = Column(String(50), nullable=False)
    description = Column(String, nullable=False)
    performed_by = Column(String(100), nullable=False)
    maintenance_date = Column(DateTime, nullable=False)
    cost = Column(Numeric(12, 2), default=0.0)
    next_schedule = Column(DateTime)

    hardware = relationship("Hardware", back_populates="maintenance_logs")

def init_db():
    Base.metadata.create_all(bind=engine)