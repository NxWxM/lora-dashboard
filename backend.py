from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles 
from pydantic import BaseModel 
from starlette.responses import FileResponse
from starlette.exceptions import HTTPException
from starlette.status import HTTP_404_NOT_FOUND
import asyncio
import json
import sqlite3
import datetime
import os 

# --- Pydantic Model (Requires 'pydantic' in requirements.txt) ---
class SensorData(BaseModel):
    sen_1: float
    sen_2: float
    sen_3: float
    sen_4: float
    label: str

app = FastAPI()
clients = set()

# --- Static Files Mount ---
# This is for assets like CSS/JS/images/etc.
app.mount("/static", StaticFiles(directory="static"), name="static") 

# Helper function to serve files and log 404s
def serve_html_file(filename):
    file_path = os.path.join("static", filename)
    if not os.path.exists(file_path):
        print(f"[FILE_ERROR] File not found: {file_path}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"File {filename} not found.")
    return FileResponse(file_path)


# --- Root Endpoint: Guarantees pg1.html is served at / ---
@app.get("/")
async def get_root():
    print("[ROUTE] --- Serving Root (/) -> pg1.html ---")
    return serve_html_file("pg1.html")

# --- Dashboard Endpoint: Guarantees dashboard.html is served at /dashboard.html ---
@app.get("/dashboard.html")
async def get_dashboard():
    print("[ROUTE] Serving /dashboard.html")
    return serve_html_file("dashboard.html")


# --- Database Setup ---
DB_PATH = "sensor.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_1 FLOAT,
    sensor_2 FLOAT,
    sensor_3 FLOAT,
    sensor_4 FLOAT,
    label TEXT
)""")
conn.commit()    

# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    q = asyncio.Queue()
    clients.add(q)
    print(f"[WS] New client connected. Total clients: {len(clients)}")
    try:
        while True:
            data = await q.get()            
            await ws.send_text(json.dumps(data))
    except WebSocketDisconnect:
        print("[WS] Client disconnected.")
    except Exception as e:
        print(f"[WS] WebSocket Error: {e}")
    finally:
        clients.discard(q)
        try:
            await ws.close()
        except Exception:
            pass


# --- POST Endpoint to Receive and Broadcast Sensor Data ---
@app.post("/sensor")
async def post_sensor(data: SensorData):
    
    payload = data.dict()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. CRITICAL LOGGING STEP
    print(f"[POST] {timestamp} Received data: {payload}")
    
    # 2. Save data to the database
    try:
        c.execute(
            "INSERT INTO sensor_data (sensor_1, sensor_2, sensor_3, sensor_4, label) VALUES (?, ?, ?, ?, ?)",
            (payload["sen_1"], payload["sen_2"], payload["sen_3"], payload["sen_4"], payload["label"])
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] Database insertion error: {e}")

    # 3. Broadcast the data
    for q in list(clients):
        try:
            await q.put(payload)
        except Exception as e:
            print(f"[POST] Error broadcasting data to a client: {e}")

    return {"status": "received and broadcasted"}
