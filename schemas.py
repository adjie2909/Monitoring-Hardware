from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from sqlalchemy import Column
from database import Base
from sqlalchemy.orm import relationship

# --- Database Models ---
# (These are kept here if needed for schema validation, 
# but ideally they should be in models.py)
# Since they are already in models.py, we just need the logic.

class HealthStatusCalculator:
    @staticmethod
    def get_health(hardware):
        if not hardware.maintenance_logs:
            return "No Schedule", None
        logs = sorted(hardware.maintenance_logs, key=lambda x: x.next_schedule or date.today(), reverse=True)
        latest = logs[0]
        today = date.today()
        if latest.next_schedule is None:
            return "No Schedule", ""
        diff = (latest.next_schedule.date() - today).days
        if diff < 0:
            return "Overdue", latest.next_schedule.strftime("%Y-%m-%d")
        elif diff <= 7:
            return "Upcoming", latest.next_schedule.strftime("%Y-%m-%d")
        else:
            return "Good", latest.next_schedule.strftime("%Y-%m-%d")

class HardwareCreate(BaseModel):
    asset_tag: str = Field(..., min_length=1)
    device_name: str = Field(..., min_length=1)
    category: str = Field(..., pattern=r"^(PC|Printer Thermal|Switch|UPS|Scanner)$")
    location: str = Field(..., min_length=1)
    ip_address: Optional[str] = None
    purchase_date: Optional[date] = None
    serial_number: Optional[str] = None
    serial_number: Optional[str] = None

class HardwareUpdate(BaseModel):
    asset_tag: Optional[str] = None
    device_name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    purchase_date: Optional[date] = None
    serial_number: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(Active|Under Maintenance|Retired)$")
    serial_number: Optional[str] = None

class MaintenanceCreate(BaseModel):
    hardware_id: int = Field(..., gt=0)
    maintenance_type: str = Field(..., pattern=r"^(Preventive|Repair|Part Replacement)$")
    description: str = Field(..., min_length=1)
    performed_by: str = Field(..., min_length=1)
    maintenance_date: date = Field(..., ge=date.today())
    cost: float = Field(0.0, ge=0)
    next_schedule: Optional[date] = None

class MaintenanceUpdate(BaseModel):
    maintenance_type: Optional[str] = None
    description: Optional[str] = None
    performed_by: Optional[str] = None
    maintenance_date: Optional[date] = None
    cost: Optional[float] = None
    next_schedule: Optional[date] = None

class HardwareOut(BaseModel):
    id: int
    asset_tag: str
    device_name: str
    category: str
    location: str
    ip_address: Optional[str] = None
    purchase_date: Optional[date] = None
    serial_number: Optional[str] = None
    serial_number: Optional[str] = None
    status: str
    health_status: str
    next_schedule_str: Optional[str] = None

    class Config:
        from_attributes = True

class MaintenanceOut(BaseModel):
    id: int
    hardware_id: int
    maintenance_type: str
    description: str
    performed_by: str
    maintenance_date: date
    cost: float
    next_schedule: Optional[date] = None

    class Config:
        from_attributes = True

class MaintenanceCreateOut(BaseModel):
    id: int
    hardware_id: int
    maintenance_type: str
    description: str
    performed_by: str
    maintenance_date: date
    cost: float
    next_schedule: Optional[date] = None

    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    total_assets: int
    upcoming: int
    overdue: int
    active_count: int
