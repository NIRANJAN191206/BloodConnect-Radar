from flask import Flask, render_template, request, jsonify
import sqlite3
import random
from twilio.rest import Client

app = Flask(__name__)

# --- TWILIO SMS CONFIG ---
# Replace these with your actual Twilio Console credentials
ACCOUNT_SID = "sid" 
AUTH_TOKEN = "auth token"
TWILIO_PHONE = "your twilio number"

def send_sms(to_phone, message):
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_PHONE, to=to_phone)
        print(f"✅ SMS sent to {to_phone}")
        return True
    except Exception as e:
        print(f"❌ Twilio Error: {e}")
        return False

# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect("blood_bank.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY, name TEXT, blood TEXT, phone TEXT, city TEXT, lat REAL, lon REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, patient TEXT, blood TEXT, hospital TEXT, phone TEXT, city TEXT)")
init_db()

CITY_COORDS = {"CHENNAI": [13.08, 80.27], "MUMBAI": [19.07, 72.87], "DELHI": [28.61, 77.20], "BANGALORE": [12.97, 77.59],"PUDUCHERRY": [11.9416, 79.8083],
    "PONDICHERRY": [11.9416, 79.8083]}

# --- ROUTES ---
# 1. This is now your Landing Page (The animation with the blood drop)
@app.route('/')
def landing(): 
    return render_template('landing.html')

# 2. This is your Main Hub/Dashboard (where the buttons for Donor/Receiver are)
@app.route('/dashboard')
def home(): 
    return render_template('index.html')

# 3. Keep these the same
@app.route('/donor_page')
def donor_page(): 
    return render_template('donor.html')

@app.route('/receiver_page')
def receiver_page(): 
    return render_template('receiver.html')

@app.route('/map_page')
def map_page(): 
    return render_template('map.html')
# REGISTER DONOR
@app.route('/api/register_donor', methods=['POST'])
def reg_donor():
    data = request.json
    city = data['city'].upper().strip()
    base = CITY_COORDS.get(city, [20.59, 78.96])
    lat, lon = base[0] + random.uniform(-0.02, 0.02), base[1] + random.uniform(-0.02, 0.02)
    
    with sqlite3.connect("blood_bank.db") as conn:
        conn.execute("INSERT INTO donors (name, blood, phone, city, lat, lon) VALUES (?,?,?,?,?,?)",
                     (data['name'], data['blood'].upper(), data['phone'], data['city'], lat, lon))
    return jsonify({"status": "success"})

# RECEIVER REQUEST + AUTOMATIC SMS
@app.route('/api/request_blood', methods=['POST'])
def reg_request():
    data = request.json
    blood_needed = data['blood'].upper()
    
    # 1. Save the request to the database
    with sqlite3.connect("blood_bank.db") as conn:
        conn.execute("INSERT INTO requests (patient, blood, hospital, phone, city) VALUES (?,?,?,?,?)",
                     (data['patient'], blood_needed, data['hospital'], data['phone'], data['city']))
    
    # 2. Find matching donors and SEND SMS
    with sqlite3.connect("blood_bank.db") as conn:
        conn.row_factory = sqlite3.Row
        matching_donors = conn.execute("SELECT phone FROM donors WHERE blood = ?", (blood_needed,)).fetchall()
        
        count = 0
        for donor in matching_donors:
            msg = f"🚨 URGENT: {blood_needed} blood needed for {data['patient']} at {data['hospital']}. Contact: {data['phone']}"
            if send_sms(donor['phone'], msg):
                count += 1
            
    return jsonify({"status": "success", "donors_notified": count})

# SEARCH FOR MAP
@app.route('/api/get_donors')
def get_donors():
    bg = request.args.get("blood", "").upper()
    with sqlite3.connect("blood_bank.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM donors WHERE blood = ?", (bg,))
        return jsonify([dict(r) for r in cur.fetchall()])

if __name__ == "__main__":
    app.run(debug=True)