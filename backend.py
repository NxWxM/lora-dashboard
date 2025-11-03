# backend.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import Request
import asyncio
import json
import sqlite3
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse

app = FastAPI()
clients = set()

app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/pg1.html")

conn = sqlite3.connect("sensor.db", check_same_thread=False)
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

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    q = asyncio.Queue()
    clients.add(q)
    try:
        while True:
            data = await q.get()            # wait for new broadcast
            await ws.send_text(json.dumps(data))
    except WebSocketDisconnect:
        # client disconnected
        pass
    except Exception as e:
        print("websocket error:", e)
    finally:
        clients.discard(q)
        try:
            await ws.close()
        except Exception:
            pass

  
    



# POST endpoint to receive sensor data and broadcast it
@app.post("/sensor")
async def post_sensor(request: Request):
    payload = await request.json()  # expect JSON like {"sen_1":..., "sen_2":...}
    # broadcast to all connected clients
    for q in list(clients):
        try:
            await q.put(payload)
            c.execute("INSERT INTO sensor_data (sensor_1,sensor_2 ,sensor_3,sensor_4,label) VALUES (?,?,?,?,?)",
              (payload["sen_1"],payload["sen_2"],payload["sen_3"],payload["sen_4"],payload["label"]))
            conn.commit()
        except Exception as e:
            print("broadcast error:", e)
    return {"status": "ok", "received": payload}

