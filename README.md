# 🅿️ ParkSmart – Vehicle Parking Management System

## Tech Stack
- **Backend**: Python Flask
- **Database**: SQLite (auto-created)
- **Frontend**: HTML, CSS, JavaScript (Vanilla)

---

## 📁 Project Structure
```
parking_system/
├── app.py                  # Main Flask application
├── requirements.txt
├── database/
│   └── parking.db          # Auto-created on first run
└── templates/
    ├── base.html           # Shared layout + navbar
    ├── index.html          # Dashboard
    ├── entry.html          # Vehicle Entry
    ├── exit.html           # Exit & Payment
    ├── slots.html          # Slot Map
    ├── admin_login.html    # Admin Login
    └── admin_dashboard.html# Admin Panel
```

---

## 🚀 How to Run

### Step 1 – Install dependencies
```bash
pip install flask
```

### Step 2 – Run the app
```bash
cd parking_system
python app.py
```

### Step 3 – Open browser
```
http://127.0.0.1:5000
```

---

## 🔑 Default Admin Credentials
- **Username**: `admin`
- **Password**: `admin123`

---

## ✅ Features

| Feature | Description |
|---|---|
| Vehicle Entry | Register vehicle, assign slot, generate Booking ID |
| Vehicle Exit | Search by vehicle no. or booking ID, auto-calculate fare |
| Payment System | Cash / UPI / Card, fare based on hours × rate |
| Slot Management | 20 slots (VIP / Regular / Two-Wheeler), real-time status |
| Admin Dashboard | Total revenue, vehicle records, payment history, slot utilization |

---

## 💰 Parking Rates
| Vehicle Type | Rate per Hour |
|---|---|
| Two-Wheeler | ₹20 |
| Car | ₹40 |
| Bus / Truck | ₹80 |

---

## 📊 Database Tables
- `slots` – Parking slot info and status
- `vehicles` – Vehicle entry/exit records
- `payments` – Payment transactions
- `admin` – Admin login credentials
