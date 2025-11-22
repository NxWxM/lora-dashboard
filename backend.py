from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Request
from fastapi.staticfiles import StaticFiles 
from pydantic import BaseModel 
from starlette.responses import FileResponse, RedirectResponse # <-- IMPORTANT: RedirectResponse is added
from starlette.exceptions import HTTPException
from starlette.status import HTTP_404_NOT_FOUND
import asyncio
import json
import sqlite3
import datetime
import os 
from sqlalchemy import create_engine, text
from fastapi import FastAPI, Request, Form, Response, status, Depends, HTTPException#!newly added
from fastapi.responses import HTMLResponse, RedirectResponse#!newly added
from fastapi import FastAPI, Request#!newly added
from fastapi.templating import Jinja2Templates #!newly added
from fastapi.responses import JSONResponse#!newly added
from datetime import datetime, timedelta#!newly added
import random#!newly added
from fastapi import Query#!newly added



# --- Pydantic Model for Data Integrity (Requires 'pydantic' in requirements.txt) ---
class SensorData(BaseModel):
    sen_1: float
    sen_2: float
    sen_3: float
    sen_4: float
    sen_5: float
    label: str
    channel:float

app = FastAPI()
clients = set()

# --- Static Files Mount ---
# This is for assets like CSS/JS/images/etc., served at /static/
app.mount("/static", StaticFiles(directory="static"), name="static") 

# Helper function to serve files reliably
def serve_html_file(filename):
    file_path = os.path.join("static", filename)
    if not os.path.exists(file_path):
        # If the file doesn't exist, log an error and raise a 404
        print(f"[FILE_ERROR] File not found: {file_path}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"File {filename} not found.")
    return FileResponse(file_path)


# --- Root Endpoint: Forces Redirect to pg1.html ---
@app.get("/")
async def get_root():
    # CRITICAL FIX: Redirect the browser to the explicit pg1.html route.
    # This bypasses any server-side static file prioritization.
    return RedirectResponse(url="/pg1.html", status_code=307) 
# --- Landing Page Endpoint: Guarantees pg1.html is served at /pg1.html ---
@app.get("/pg1.html")
async def get_pg1_page():
    return serve_html_file("pg1.html")
@app.get("/homepage.html")
async def get_pg1_page():
    return serve_html_file("pg1.html")
@app.get("/admin_dashboard.html")#!newly added
async def get_pg1_page():
    return serve_html_file("admin_dashboard.html")
# --- Dashboard Endpoint: Guarantees dashboard.html is served at /dashboard.html ---

#!newly added for multiple channels
@app.get("/channel_dashboard")
async def get_dashboard():
    return serve_html_file("channel_dashboard.html")
@app.get("/show_dashboard")
async def get_dashboard(request: Request):
    chann = request.query_params.get("channel")
    print(chann)
    return RedirectResponse(url=f"/dashboard.html?channel={chann}")
@app.get("/dashboard.html")
async def get_dashboard_page():
    return serve_html_file("dashboard.html")
    
    



    



def calculate_age(born):#!newly added
    today = datetime.utcnow().date()
    age = today.year - born.year
    # Adjust age if the birthday hasn't occurred yet this year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return age





# --- Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id SERIAL PRIMARY KEY,
            date TEXT,
            time TEXT,
            sensor_1 FLOAT,
            sensor_2 FLOAT,
            sensor_3 FLOAT,
            sensor_4 FLOAT,
            sensor_5 FLOAT,
            label TEXT,
            channel FLOAT
        )
    """))
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


#--- POST Endpoint to Receive and Broadcast Sensor Data ---
@app.post("/sensor")
async def post_sensor(data: SensorData):
    
    payload = data.model_dump()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    # 1. Log the received data
    print(f"[POST] {now.strftime('%Y-%m-%d %H:%M:%S')} Received data: {payload}")
    
    # 2. Save data to the database
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO sensor_data (date, time, sensor_1, sensor_2, sensor_3, sensor_4, sensor_5, label, channel) VALUES (:date, :time, :s1, :s2, :s3, :s4, :s5, :label, :channel)"),
                {
                    "date": date_str,
                    "time": time_str,
                    "s1": payload["sen_1"],
                    "s2": payload["sen_2"],
                    "s3": payload["sen_3"],
                    "s4": payload["sen_4"],
                    "s5": payload["sen_5"],
                    "label": payload["label"],
                    "channel": payload["channel"],
                },
            )
    except Exception as e:
        print(f"[DB] Database insertion error: {e}")

    # 3. Broadcast the data
    for q in list(clients):
        try:
            await q.put(payload)
        except Exception as e:
            print(f"[POST] Error broadcasting data to a client: {e}")

    return {"status": "received and broadcasted"}

#!newly added(Admin login page)
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return  serve_html_file("login.html")

@app.post("/login")
def login(response: Response,request: Request, username: str = Form(...), password: str = Form(...)):
    with engine.begin() as db:
        Trust=True
        
        query = text("SELECT * FROM users WHERE username = :u")
        result = db.execute(query, {"u": username}).fetchone()
        if  result==None:
             print("invalid username")
             return "invalid username"
            
        elif password != result[2]:#0-id,1-username,2-password
            print("Invalid password")
            return "Invalid password"
            
        resp = JSONResponse(
            status_code=200,
            content={
                "success": True,
                "redirect": "/admin_dashboard"
                    }
        )

        resp.set_cookie(
            key="admin_user",
            value=result[1],
            httponly=True,
            samesite="lax"
        )

        return resp
        #I ran your code but my backend dont get the post request

@app.post("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@app.get("/admin_dashboard", response_class=HTMLResponse)
def admin_dash():
    response = RedirectResponse(url="admin_dashboard.html", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

#!function for admin graph(newly added)
@app.get("/api/chart")
def last_7_days():
    labels = []
    temperature=[]
    humidity=[]
    gas1=[]
    gas2=[]
    gas3=[]

    today = datetime.utcnow().date()
    with engine.begin() as db:

    # Generate exactly 7 days
        for i in range(7):
            day = today - timedelta(days=6 - i)
            query = text("""
            SELECT
                 AVG(sensor_1) AS avg_temp,
                 AVG(sensor_2) AS avg_humd,
                 AVG(sensor_3) AS avg_gas1,
                 AVG(sensor_4) AS avg_gas2,
                 AVG(sensor_5) AS avg_gas3
            FROM sensor_data
             WHERE CAST(date AS date) = :d
            """)
        
            row = db.execute(query, {"d": day}).fetchone()
            
            if row and row.avg_temp is not None:
                temperature.append( float(row.avg_temp))
            else:
                temperature.append(0)
            if row and row.avg_humd is not None:
                humidity.append( float(row.avg_humd))
            else:
                humidity.append(0)
            if row and row.avg_gas1 is not None:
                gas1.append( float(row.avg_gas1))
            else:
                gas1.append(0)
            if row and row.avg_gas2 is not None:
                gas2.append( float(row.avg_gas2))
            else:
                gas2.append(0)
            if row and row.avg_gas3 is not None:
                gas3.append( float(row.avg_gas3))
            else:
                gas3.append(0)

            labels.append(day.strftime("%d"))
            
        

    return JSONResponse({
        "labels": labels,
        "temperature": temperature,
        "humidity": humidity,
        "gas1": gas1,
        "gas2": gas2,
        "gas3": gas3
    })            

#!function for find users in admin(newly added)
@app.get("/api/employees")
async def get_employee(request: Request):
    username = request.query_params.get("username")
    print(f"Searching for employee: {username}")

    # Convert input to lowercase for easier matching
    user_key = username.lower()
    with engine.begin() as db:
    
        query = text("SELECT * FROM employees WHERE name = :u")
        employee = db.execute(query, {"u": user_key}).fetchone()
        
        if not employee:
            # Returns a 404 error if user isn't in the list
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Calculate age dynamically before sending back
        current_age = calculate_age(employee.birthday)
        
        # Return the JSON response
        return {
            "name": employee.name,
            "birthday": employee.birthday,
            "role": employee.role,
            "age": current_age, # Computed value
            
    }
#!function for add new employees in admin(newly added)
class Employee(BaseModel):
    name: str
    birthday: str
    role: str
@app.post("/api/add_employees")
def add_employee(emp: Employee):
    date_object = datetime.strptime(emp.birthday, "%Y-%m-%d").date()
    with engine.begin() as db:
        find_quary = text("SELECT * FROM employees WHERE name = :n")
        found_result = db.execute(find_quary, {"n": emp.name.lower()}).fetchone()
        if found_result:
            return {"status": "Employee already exists","data": emp}
        else:
            query = text("INSERT INTO employees (name, birthday, role) VALUES (:n, :b, :r)")
            db.execute(query, {"n": emp.name.lower(), "b": date_object, "r": emp.role})
            print(emp.name+" added successfully")
            return {"status": "Employee added successfully","data": emp}