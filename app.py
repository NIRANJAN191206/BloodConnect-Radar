from flask import Flask, render_template, request, jsonify
import sqlite3
import random
from twilio.rest import Client

app = Flask(__name__)

# --- TWILIO CONFIG ---
ACCOUNT_SID = "acc sid" 
AUTH_TOKEN = "auth_token"
TWILIO_PHONE = "+1xxxxxxxx"

def send_sms(to_phone, message):
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_PHONE, to=to_phone)
        return True
    except: return False

# --- DB SETUP ---
def init_db():
    with sqlite3.connect("blood_bank.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY, name TEXT, blood TEXT, phone TEXT, city TEXT, lat REAL, lon REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, patient TEXT, blood TEXT, hospital TEXT, phone TEXT, city TEXT)")
init_db()

CITY_COORDS = {"PUDUCHERRY": [11.94, 79.80], "CHENNAI": [13.08, 80.27]}

# 1. Landing Page (First view)
@app.route('/')
def landing(): 
    return render_template('landing.html')

# 2. Dashboard (The Index - Central Hub)
@app.route('/dashboard')
def dashboard(): 
    return render_template('index.html')

# 3. Individual Action Pages
@app.route('/donor_page')
def donor_page(): 
    return render_template('donor.html')

@app.route('/receiver_page')
def receiver_page(): 
    return render_template('receiver.html')

@app.route('/map_page')
def map_page(): 
    return render_template('map.html')

@app.route('/api/register_donor', methods=['POST'])
def reg_donor():
    data = request.json
    city = data['city'].upper().strip()
    base = CITY_COORDS.get(city, [11.94, 79.80])
    lat, lon = base[0] + random.uniform(-0.02, 0.02), base[1] + random.uniform(-0.02, 0.02)
    with sqlite3.connect("blood_bank.db") as conn:
        conn.execute("INSERT INTO donors (name, blood, phone, city, lat, lon) VALUES (?,?,?,?,?,?)",
                     (data['name'], data['blood'].upper(), data['phone'], city, lat, lon))
    return jsonify({"status": "success"})

@app.route('/api/request_blood', methods=['POST'])
def reg_request():
    data = request.json
    blood = data['blood'].upper()
    with sqlite3.connect("blood_bank.db") as conn:
        conn.execute("INSERT INTO requests (patient, blood, hospital, phone, city) VALUES (?,?,?,?,?)",
                     (data['patient'], blood, data['hospital'], data['phone'], data['city']))
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT name, phone, city FROM donors WHERE blood = ?", (blood,))
        donors = [dict(row) for row in cur.fetchall()]
    
    for d in donors:
        send_sms(d['phone'], f"Emergency! {blood}  Blood needed for {data['patient']} at {data['hospital']}. Call {data['phone']}")
    
    return jsonify({"status": "success", "donors": donors})

@app.route('/api/get_donors')
def get_donors():
    with sqlite3.connect("blood_bank.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM donors")
        return jsonify([dict(r) for r in cur.fetchall()])

if __name__ == "__main__":
    app.run(debug=True)