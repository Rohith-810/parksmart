from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from datetime import datetime
import sqlite3
import os
import random
import string

app = Flask(__name__)
app.secret_key = 'parking_secret_key_2024'

DB_PATH = 'database/parking.db'

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_number TEXT UNIQUE NOT NULL,
        slot_type TEXT NOT NULL DEFAULT 'regular',
        status TEXT NOT NULL DEFAULT 'available'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_number TEXT NOT NULL,
        vehicle_type TEXT NOT NULL,
        owner_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        slot_id INTEGER,
        entry_time TEXT,
        exit_time TEXT,
        amount_paid REAL DEFAULT 0,
        status TEXT DEFAULT 'parked',
        booking_id TEXT UNIQUE,
        FOREIGN KEY(slot_id) REFERENCES slots(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        booking_id TEXT,
        amount REAL,
        payment_mode TEXT,
        payment_time TEXT,
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    # Seed slots A1-A5 (VIP), B1-B10 (Regular), C1-C5 (Two-Wheeler)
    existing = c.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
    if existing == 0:
        for i in range(1, 6):
            c.execute("INSERT INTO slots (slot_number, slot_type) VALUES (?, ?)", (f'A{i}', 'vip'))
        for i in range(1, 11):
            c.execute("INSERT INTO slots (slot_number, slot_type) VALUES (?, ?)", (f'B{i}', 'regular'))
        for i in range(1, 6):
            c.execute("INSERT INTO slots (slot_number, slot_type) VALUES (?, ?)", (f'C{i}', 'two-wheeler'))

    # Default admin
    c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin123'))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────
def generate_booking_id():
    return 'BK' + ''.join(random.choices(string.digits, k=6))

def calculate_fare(entry_time_str, exit_time_str, vehicle_type):
    fmt = "%Y-%m-%d %H:%M:%S"
    entry = datetime.strptime(entry_time_str, fmt)
    exit_ = datetime.strptime(exit_time_str, fmt)
    hours = max(1, (exit_ - entry).seconds // 3600 + (1 if (exit_ - entry).seconds % 3600 > 0 else 0))
    rates = {'two-wheeler': 20, 'car': 40, 'bus': 80}
    rate = rates.get(vehicle_type.lower(), 40)
    return hours * rate, hours

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
    occupied = conn.execute("SELECT COUNT(*) FROM slots WHERE status='occupied'").fetchone()[0]
    available = total - occupied
    today_earnings = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE DATE(payment_time)=DATE('now')"
    ).fetchone()[0]
    recent = conn.execute(
        "SELECT v.*, s.slot_number FROM vehicles v JOIN slots s ON v.slot_id=s.id WHERE v.status='parked' ORDER BY v.entry_time DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template('index.html', total=total, occupied=occupied,
                           available=available, today_earnings=today_earnings, recent=recent)

# ── ENTRY ──
@app.route('/entry', methods=['GET', 'POST'])
def entry():
    conn = get_db()
    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number'].upper().strip()
        vehicle_type   = request.form['vehicle_type']
        owner_name     = request.form['owner_name'].strip()
        phone          = request.form['phone'].strip()
        slot_id        = request.form['slot_id']

        # Check already parked
        existing = conn.execute(
            "SELECT id FROM vehicles WHERE vehicle_number=? AND status='parked'", (vehicle_number,)
        ).fetchone()
        if existing:
            flash('Vehicle is already parked!', 'error')
            return redirect(url_for('entry'))

        booking_id  = generate_booking_id()
        entry_time  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            "INSERT INTO vehicles (vehicle_number, vehicle_type, owner_name, phone, slot_id, entry_time, status, booking_id) VALUES (?,?,?,?,?,?,?,?)",
            (vehicle_number, vehicle_type, owner_name, phone, slot_id, entry_time, 'parked', booking_id)
        )
        conn.execute("UPDATE slots SET status='occupied' WHERE id=?", (slot_id,))
        conn.commit()

        flash(f'Vehicle entry successful! Booking ID: {booking_id}', 'success')
        conn.close()
        return redirect(url_for('index'))

    slots = conn.execute("SELECT * FROM slots WHERE status='available' ORDER BY slot_type, slot_number").fetchall()
    conn.close()
    return render_template('entry.html', slots=slots)

# ── EXIT / PAYMENT ──
@app.route('/exit', methods=['GET', 'POST'])
def exit_vehicle():
    conn = get_db()
    vehicle_data = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'search':
            query = request.form['query'].upper().strip()
            vehicle_data = conn.execute(
                "SELECT v.*, s.slot_number FROM vehicles v JOIN slots s ON v.slot_id=s.id WHERE (v.vehicle_number=? OR v.booking_id=?) AND v.status='parked'",
                (query, query)
            ).fetchone()
            if not vehicle_data:
                flash('No active parking found!', 'error')

        elif action == 'checkout':
            vehicle_id   = request.form['vehicle_id']
            payment_mode = request.form['payment_mode']
            exit_time    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            vehicle = conn.execute("SELECT * FROM vehicles WHERE id=?", (vehicle_id,)).fetchone()
            amount, hours = calculate_fare(vehicle['entry_time'], exit_time, vehicle['vehicle_type'])

            conn.execute(
                "UPDATE vehicles SET exit_time=?, amount_paid=?, status='exited' WHERE id=?",
                (exit_time, amount, vehicle_id)
            )
            conn.execute("UPDATE slots SET status='available' WHERE id=?", (vehicle['slot_id'],))
            conn.execute(
                "INSERT INTO payments (vehicle_id, booking_id, amount, payment_mode, payment_time) VALUES (?,?,?,?,?)",
                (vehicle_id, vehicle['booking_id'], amount, payment_mode, exit_time)
            )
            conn.commit()
            flash(f'Checkout successful! Amount Paid: ₹{amount} for {hours} hour(s)', 'success')
            conn.close()
            return redirect(url_for('index'))

    conn.close()
    return render_template('exit.html', vehicle=vehicle_data)

# ── SLOTS ──
@app.route('/slots')
def slots():
    conn = get_db()
    all_slots = conn.execute("SELECT s.*, v.vehicle_number, v.owner_name FROM slots s LEFT JOIN vehicles v ON s.id=v.slot_id AND v.status='parked' ORDER BY s.slot_type, s.slot_number").fetchall()
    conn.close()
    return render_template('slots.html', slots=all_slots)

# ── ADMIN ──
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        admin = conn.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password)).fetchone()
        conn.close()
        if admin:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials!', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    total_vehicles  = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    active_vehicles = conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='parked'").fetchone()[0]
    total_earnings  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0]
    today_earnings  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE DATE(payment_time)=DATE('now')").fetchone()[0]
    slot_stats      = conn.execute("SELECT slot_type, COUNT(*) as total, SUM(CASE WHEN status='occupied' THEN 1 ELSE 0 END) as occupied FROM slots GROUP BY slot_type").fetchall()
    all_vehicles    = conn.execute("SELECT v.*, s.slot_number FROM vehicles v LEFT JOIN slots s ON v.slot_id=s.id ORDER BY v.entry_time DESC LIMIT 20").fetchall()
    payments        = conn.execute("SELECT p.*, v.vehicle_number FROM payments p JOIN vehicles v ON p.vehicle_id=v.id ORDER BY p.payment_time DESC LIMIT 10").fetchall()
    conn.close()
    return render_template('admin_dashboard.html',
                           total_vehicles=total_vehicles, active_vehicles=active_vehicles,
                           total_earnings=total_earnings, today_earnings=today_earnings,
                           slot_stats=slot_stats, all_vehicles=all_vehicles, payments=payments)

# ── API: Slot availability (JSON) ──
@app.route('/api/slots')
def api_slots():
    conn = get_db()
    slots = conn.execute("SELECT * FROM slots ORDER BY slot_number").fetchall()
    conn.close()
    return jsonify([dict(s) for s in slots])

if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    init_db()
    import os
port = int(os.environ.get("PORT", 5000))
app.run(host='0.0.0.0', port=port, debug=False)
