import io
import asyncio
import platform
import re
from datetime import datetime, date
from typing import Optional, cast
import subprocess
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Hardware, MaintenanceLog, init_db
from schemas import (
    HardwareCreate, HardwareUpdate, MaintenanceCreate, MaintenanceCreateOut,
    DashboardSummary, HealthStatusCalculator
)

templates = Jinja2Templates(directory="templates")

# ── Dependency DB ──────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Ping Utility ───────────────────────────────────────
async def ping_ip(ip: Optional[str], timeout: float = 2.0) -> dict:
    if not ip or not ip.strip():
        return {"online": False, "latency_ms": None, "status": "No IP"}
    
    clean_ip = ip.strip()
    is_win = platform.system().lower() == "windows"
    
    # Windows: -n 1 (1 paket), -w 2000 (timeout 2000ms)
    # Linux/Mac: -c 1 (1 paket), -W 2 (timeout 2 detik)
    cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), clean_ip] if is_win else ["ping", "-c", "1", "-W", str(int(timeout)), clean_ip]

    def _execute():
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout + 1.0
            )
            output = res.stdout
            
            # Cek indikasi gagal / unreachable
            if res.returncode != 0 or "unreachable" in output.lower() or "timed out" in output.lower() or "rto" in output.lower():
                return {"online": False, "latency_ms": None, "status": "Offline"}

            # Regex pencocokan latensi untuk bahasa Inggris maupun bahasa Indonesia (time=..ms / waktu=..ms)
            match = re.search(r"(?:time|waktu)[=<]\s*(\d+(?:\.\d+)?)\s*ms", output, re.IGNORECASE)
            latency = float(match.group(1)) if match else 1.0
            return {"online": True, "latency_ms": latency, "status": "Online"}
        except Exception:
            return {"online": False, "latency_ms": None, "status": "Offline"}

    # Jalankan subprocess di worker thread agar tidak memblokir event loop dan aman di Windows
    return await asyncio.to_thread(_execute)

# ── App ────────────────────────────────────────────────
app = FastAPI(title="IT Hardware Health Tracker", version="1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.on_event("startup")
def startup():
    init_db()

# ── Web UI Routes ──────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/hardware/{hw_id}", response_class=HTMLResponse)
def device_detail_page(hw_id: int, request: Request, db: Session = Depends(get_db)):
    hw = db.query(Hardware).filter_by(id=hw_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware not found")
    logs = db.query(MaintenanceLog).filter_by(hardware_id=hw_id).order_by(MaintenanceLog.maintenance_date.desc()).all()
    label, sched_str = HealthStatusCalculator.get_health(hw)
    
    hw.health_label = label
    hw.health_color = {
        "Overdue": "bg-red-500 text-white",
        "Upcoming": "bg-yellow-500 text-black",
        "Good": "bg-green-500 text-white",
        "No Schedule": "bg-gray-400 text-gray-800"
    }[label]

    return templates.TemplateResponse(
        request=request,
        name="device_detail.html",
        context={"hw": hw, "maintenance_logs": logs}
    )

# ── Ping API Endpoints ─────────────────────────────────
@app.get("/api/hardware/{hw_id}/ping")
async def ping_device(hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).filter_by(id=hw_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware not found")
    
    ip_val = cast(Optional[str], getattr(hw, "ip_address", None))
    res = await ping_ip(ip_val)
    return {"hardware_id": hw.id, "ip_address": ip_val, **res}

@app.get("/api/hardware/ping-all")
async def ping_all_devices(db: Session = Depends(get_db)):
    all_hw = db.query(Hardware).all()
    tasks = [ping_ip(cast(Optional[str], getattr(hw, "ip_address", None))) for hw in all_hw]
    results = await asyncio.gather(*tasks)
    return {
        hw.id: {
            "asset_tag": hw.asset_tag,
            "ip_address": cast(Optional[str], getattr(hw, "ip_address", None)),
            **res
        }
        for hw, res in zip(all_hw, results)
    }

# ── Dashboard KPIs ─────────────────────────────────────
@app.get("/api/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    all_hardware = db.query(Hardware).all()
    totals = {"total_assets": len(all_hardware), "overdue": 0, "upcoming": 0, "active_count": 0}
    for hw in all_hardware:
        label, _ = HealthStatusCalculator.get_health(hw)
        if label == "Overdue":
            totals["overdue"] += 1
        elif label == "Upcoming":
            totals["upcoming"] += 1
        elif str(getattr(hw, "status", "")) == "Active":
            totals["active_count"] += 1
    return DashboardSummary(**totals)

# ── All Hardware List ──────────────────────────────────
@app.get("/api/hardware")
def list_hardware(db: Session = Depends(get_db)):
    all_hw = db.query(Hardware).all()
    results = []
    for hw in all_hw:
        label, sched_str = HealthStatusCalculator.get_health(hw)
        purchase_dt = getattr(hw, "purchase_date", None)
        results.append({
            "id": hw.id,
            "asset_tag": hw.asset_tag,
            "device_name": hw.device_name,
            "category": hw.category,
            "location": hw.location,
            "ip_address": hw.ip_address,
            "purchase_date": purchase_dt.isoformat() if purchase_dt is not None else None,
            "status": hw.status,
            "health_status": label,
            "health_color": {
                "Overdue": "bg-red-500 text-white",
                "Upcoming": "bg-yellow-500 text-black",
                "Good": "bg-green-500 text-dark-green",
                "No Schedule": "bg-gray-400 text-gray-800"
            }[label],
            "next_schedule_str": sched_str,
        })
    return results

# ── Add Hardware ───────────────────────────────────────
@app.post("/api/hardware/add", response_model=HardwareCreate)
def add_hardware(hw: HardwareCreate, db: Session = Depends(get_db)):
    existing = db.query(Hardware).filter_by(asset_tag=hw.asset_tag.upper()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Asset tag already exists")
    new_hw = Hardware(
        asset_tag=hw.asset_tag.upper(),
        device_name=hw.device_name,
        category=hw.category,
        location=hw.location,
        ip_address=hw.ip_address,
        purchase_date=hw.purchase_date,
    )
    db.add(new_hw)
    db.commit()
    db.refresh(new_hw)
    return new_hw

# ── Device Detail API ──────────────────────────────────
@app.get("/api/hardware/{hw_id}")
def get_device_detail(hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).filter_by(id=hw_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware not found")
    logs = db.query(MaintenanceLog).filter_by(hardware_id=hw_id).order_by(MaintenanceLog.maintenance_date.desc()).all()
    label, sched_str = HealthStatusCalculator.get_health(hw)
    return {
        "hardware": hw,
        "maintenance_logs": logs,
        "health_label": label,
        "health_color": {
            "Overdue": "bg-red-500 text-white",
            "Upcoming": "bg-yellow-500 text-black",
            "Good": "bg-green-500 text-dark-green",
            "No Schedule": "bg-gray-400 text-gray-800"
        }[label],
        "next_schedule_str": sched_str,
    }

# ── Update Hardware ────────────────────────────────────
@app.put("/api/hardware/{hw_id}/update")
def update_hardware(hw_id: int, data: HardwareUpdate, db: Session = Depends(get_db)):
    hw = db.query(Hardware).filter_by(id=hw_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware not found")
    for key in data.model_dump(exclude_unset=True, exclude_none=True):
        setattr(hw, key, getattr(data, key))
    db.commit()
    db.refresh(hw)
    return {"message": "Hardware updated"}

# ── Add Maintenance Log ────────────────────────────────
@app.post("/api/maintenance/add", response_model=MaintenanceCreateOut)
def add_maintenance(log: MaintenanceCreate, db: Session = Depends(get_db)):
    hw = db.query(Hardware).filter_by(id=log.hardware_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware not found")
    new_log = MaintenanceLog(
        hardware_id=log.hardware_id,
        maintenance_type=log.maintenance_type,
        description=log.description,
        performed_by=log.performed_by,
        maintenance_date=datetime.combine(log.maintenance_date, datetime.min.time()),
        cost=log.cost,
        next_schedule=datetime.combine(log.next_schedule, datetime.min.time()) if log.next_schedule else None,
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log

# ── Export Logs as CSV ─────────────────────────────────
@app.get("/api/export/logs/csv")
def export_csv(db: Session = Depends(get_db)):
    all_logs = db.query(MaintenanceLog).order_by(MaintenanceLog.maintenance_date.desc()).all()
    rows = []
    for log in all_logs:
        hw = db.query(Hardware).filter_by(id=log.hardware_id).first()
        asset_tag = hw.asset_tag if hw else "-"
        device_name = hw.device_name if hw else "-"
        m_date = getattr(log, "maintenance_date", None)
        n_date = getattr(log, "next_schedule", None)

        rows.append(";".join([
            str(asset_tag),
            str(device_name),
            str(log.maintenance_type),
            str(log.description),
            str(log.performed_by),
            m_date.isoformat() if m_date is not None else "",
            str(log.cost),
            n_date.isoformat() if n_date is not None else ""
        ]))

    csv_header = ";".join(["Asset Tag", "Device", "Type", "Description", "Performed By", "Date", "Cost", "Next Schedule"])
    csv_content = csv_header + "\n" + "\n".join(rows)

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="maintenance_logs.csv"'}
    )

# ── Export Logs as Excel ───────────────────────────────
@app.get("/api/export/logs/excel")
def export_excel(db: Session = Depends(get_db)):
    all_logs = db.query(MaintenanceLog).order_by(MaintenanceLog.maintenance_date.desc()).all()
    records = []
    for log in all_logs:
        hw = db.query(Hardware).filter_by(id=log.hardware_id).first()
        m_date = getattr(log, "maintenance_date", None)
        n_date = getattr(log, "next_schedule", None)

        records.append({
            "Asset Tag": hw.asset_tag if hw else "-",
            "Device Name": hw.device_name if hw else "-",
            "Maintenance Type": log.maintenance_type,
            "Description": log.description,
            "Performed By": log.performed_by,
            "Date": m_date.strftime("%Y-%m-%d") if m_date is not None else "",
            "Cost (RMB)": log.cost,
            "Next Schedule": n_date.strftime("%Y-%m-%d") if n_date is not None else ""
        })

    df = pd.DataFrame(records)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="maintenance_logs.xlsx"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)