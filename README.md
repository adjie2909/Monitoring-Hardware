# 🖥️ Hardware Health Tracker

A comprehensive IT infrastructure management system designed to monitor the health, maintenance schedules, and connectivity status of hardware assets like PCs, Printers, Switches, UPS, and Scanners.

## 🌟 Features

- **Real-time Health Dashboard**: Instant overview of total assets, upcoming maintenance, overdue tasks, and active devices.
- **Live Connectivity Status**: Asynchronous ping utility to detect if devices are online or offline in real-time.
- **Automated Health Scoring**: Intelligent logic to categorize devices into *Good*, *Upcoming*, *Overdue*, or *No Schedule*.
- **Maintenance Tracking**: Comprehensive logs for every hardware unit, including maintenance types, descriptions, costs, and next scheduled dates.
- **Data Export**: Export your maintenance history directly to **CSV** and **Excel** formats for reporting.
- **Responsive Design**: Modern, mobile-friendly UI built with Tailwind CSS and a *glass-morphism* aesthetic.

## 🛠 Tech Stack

- **Backend**: Python, FastAPI
- **Database**: SQLAlchemy ORM (SQLite/PostgreSQL compatible)
- **Frontend**: Jinja2 Templates, Tailwind CSS, Vanilla JavaScript
- **Libraries**: Pandas (Data Export), SQLAlchemy, Uvicorn
- **Icons**: Font Awesome

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Pip (Python package installer)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/adjie2909/hardware-health-tracker.git
   cd hardware-health-tracker
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```
   The application will be available at `http://localhost:8000`.

## 📖 Usage Guide

1. **Add Device**: Navigate to the dashboard and click "Tambah PC Baru" to register your hardware (Asset Tag, Name, Category, Location, IP, Serial Number).
2. **Monitor Health**: The dashboard automatically calculates health based on your maintenance logs.
3. **Log Maintenance**: Add new records for every repair or preventive maintenance performed.
4. **Export Reports**: Use the export buttons at the top of the maintenance section to download history files.

## 📂 Project Structure

```text
├── main.py              # FastAPI application entry point
├── database.py          # Database connection and session management
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic models for data validation
├── templates/           # Jinja2 HTML templates
│   ├── base.html        # Layout wrapper
│   ├── dashboard.html   # Main KPI & Device list
│   └── device_detail.html # Specific device view & logs
└── static/              # Static assets (images, CSS)
```

