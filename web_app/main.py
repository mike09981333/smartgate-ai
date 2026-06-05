import os
import time
import glob
import sqlite3
from datetime import datetime
import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
from dotenv import load_dotenv
from insightface.app import FaceAnalysis

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
load_dotenv(os.path.join(PROJECT_DIR, ".env"))
RAW_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join("web_app", "data", "smartgate.db"))
DB_PATH = RAW_DB_PATH if os.path.isabs(RAW_DB_PATH) else os.path.join(PROJECT_DIR, RAW_DB_PATH)

app = FastAPI()

ARDUINO_BAUDRATE = int(os.getenv("ARDUINO_BAUDRATE", "9600"))
ARDUINO_PORT = os.getenv("ARDUINO_PORT")
ARDUINO_ENABLED = os.getenv("ARDUINO_ENABLED", "1") != "0"
ARDUINO_READY_DELAY = float(os.getenv("ARDUINO_READY_DELAY", "2"))
ACCESS_GRANTED_STATUS = "accorde"
ACCESS_DENIED_STATUS = "refuse"
DAY_NAMES_FR = {
    "Monday": "lundi",
    "Tuesday": "mardi",
    "Wednesday": "mercredi",
    "Thursday": "jeudi",
    "Friday": "vendredi",
    "Saturday": "samedi",
    "Sunday": "dimanche",
}

# Create data directories on startup
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_database():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('accorde', 'refuse')),
                similarity REAL,
                access_date TEXT NOT NULL,
                access_time TEXT NOT NULL,
                access_day TEXT NOT NULL,
                access_datetime TEXT NOT NULL,
                barrier_opened INTEGER NOT NULL DEFAULT 0,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()

def log_access_attempt(person_name, status, similarity=None, barrier_opened=False, note=None):
    now = datetime.now()
    day_name = DAY_NAMES_FR.get(now.strftime("%A"), now.strftime("%A"))
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO access_logs (
                person_name,
                status,
                similarity,
                access_date,
                access_time,
                access_day,
                access_datetime,
                barrier_opened,
                note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_name,
                status,
                similarity,
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                day_name,
                now.isoformat(timespec="seconds"),
                int(barrier_opened),
                note,
            ),
        )
        connection.commit()

init_database()

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

@app.on_event("shutdown")
def shutdown_event():
    close_arduino_connection()

# Initialize InsightFace Model
print("Initialisation du modèle InsightFace...")
face_app = FaceAnalysis(providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(320, 320))
print("Modèle prêt.")

arduino_connection = None

def find_arduino_port():
    if ARDUINO_PORT:
        return ARDUINO_PORT

    if list_ports is None:
        candidates = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
        return candidates[0] if candidates else None

    preferred_keywords = ("arduino", "usb serial", "ch340", "wch", "ttyacm", "ttyusb")
    for port in list_ports.comports():
        description = f"{port.device} {port.description} {port.manufacturer or ''}".lower()
        if any(keyword in description for keyword in preferred_keywords):
            return port.device

    candidates = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    return candidates[0] if candidates else None

def get_arduino_connection():
    global arduino_connection

    if not ARDUINO_ENABLED:
        return None

    if serial is None:
        print("Arduino désactivé: installez pyserial avec 'pip install pyserial'.")
        return None

    if arduino_connection and arduino_connection.is_open:
        return arduino_connection

    port = find_arduino_port()
    if not port:
        print("Arduino introuvable: définissez ARDUINO_PORT, par exemple /dev/ttyACM0 ou COM3.")
        return None

    try:
        arduino_connection = serial.Serial(port, ARDUINO_BAUDRATE, timeout=1)
        time.sleep(ARDUINO_READY_DELAY)
        print(f"Arduino connecté sur {port}.")
        return arduino_connection
    except serial.SerialException as exc:
        print(f"Impossible de connecter l'Arduino sur {port}: {exc}")
        arduino_connection = None
        return None

def send_arduino_command(command):
    connection = get_arduino_connection()
    if connection is None:
        return False

    try:
        connection.write(f"{command}\n".encode("utf-8"))
        connection.flush()
        print(f"Commande Arduino envoyée: {command}")
        return True
    except serial.SerialException as exc:
        print(f"Erreur pendant l'envoi vers l'Arduino: {exc}")
        close_arduino_connection()
        return False

def close_arduino_connection():
    global arduino_connection

    if arduino_connection and arduino_connection.is_open:
        arduino_connection.close()
    arduino_connection = None

def save_embedding(name, emb):
    filepath = os.path.join(EMBEDDINGS_DIR, f"{name}.npy")
    np.save(filepath, emb)

def load_all_embeddings():
    """Load all registered embeddings and return a dict {name: embedding}."""
    embeddings = {}
    if os.path.exists(EMBEDDINGS_DIR):
        for filename in os.listdir(EMBEDDINGS_DIR):
            if filename.endswith(".npy"):
                name = os.path.splitext(filename)[0]
                embeddings[name] = np.load(os.path.join(EMBEDDINGS_DIR, filename))
    return embeddings

def save_photo(name, img):
    filepath = os.path.join(PHOTOS_DIR, f"{name}.jpg")
    cv2.imwrite(filepath, img)

def is_safe_username(name):
    return bool(name) and os.path.basename(name) == name

def process_base64_image(base64_string):
    # Extract data part
    encoded_data = base64_string.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

class RegisterPayload(BaseModel):
    image: str
    name: str

class VerifyPayload(BaseModel):
    image: str

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r") as f:
        return HTMLResponse(
            content=f.read(),
            headers={"Cache-Control": "no-store"}
        )

@app.get("/users")
async def get_users():
    """Return a list of all registered users with their photo URLs."""
    users = []
    if os.path.exists(PHOTOS_DIR):
        for filename in sorted(os.listdir(PHOTOS_DIR)):
            if filename.endswith(".jpg"):
                name = os.path.splitext(filename)[0]
                users.append({
                    "name": name,
                    "photo_url": f"/data/photos/{filename}"
                })
    return {"users": users}

@app.get("/access-logs")
async def get_access_logs(limit: int = 100):
    safe_limit = max(1, min(limit, 500))
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                person_name,
                status,
                similarity,
                access_date,
                access_time,
                access_day,
                access_datetime,
                barrier_opened,
                note,
                created_at
            FROM access_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    logs = []
    for row in rows:
        logs.append(
            {
                "id": row["id"],
                "person_name": row["person_name"],
                "status": row["status"],
                "similarity": row["similarity"],
                "access_date": row["access_date"],
                "access_time": row["access_time"],
                "access_day": row["access_day"],
                "access_datetime": row["access_datetime"],
                "barrier_opened": bool(row["barrier_opened"]),
                "note": row["note"],
                "created_at": row["created_at"],
            }
        )

    return {"logs": logs}

@app.delete("/users/{name}")
async def delete_user(name: str):
    name = name.strip()
    if not is_safe_username(name):
        return JSONResponse(status_code=400, content={"message": "Nom d'utilisateur invalide."})

    photo_path = os.path.join(PHOTOS_DIR, f"{name}.jpg")
    embedding_path = os.path.join(EMBEDDINGS_DIR, f"{name}.npy")
    deleted = False

    for filepath in (photo_path, embedding_path):
        if os.path.exists(filepath):
            os.remove(filepath)
            deleted = True

    if not deleted:
        return JSONResponse(status_code=404, content={"message": "Utilisateur introuvable."})

    return {"message": f"Utilisateur {name} supprimé avec succès."}

@app.post("/register")
async def register_face(payload: RegisterPayload):
    try:
        name = payload.name.strip()
        if not name:
            return JSONResponse(status_code=400, content={"message": "Veuillez entrer un nom."})
        if not is_safe_username(name):
            return JSONResponse(status_code=400, content={"message": "Le nom ne peut pas contenir de slash."})

        img = process_base64_image(payload.image)
        faces = face_app.get(img)
        
        if len(faces) == 0:
            return JSONResponse(status_code=400, content={"message": "Aucun visage détecté."})
        elif len(faces) > 1:
            return JSONResponse(status_code=400, content={"message": "Plusieurs visages détectés. Soyez seul."})
        
        emb = faces[0].normed_embedding
        save_embedding(name, emb)
        save_photo(name, img)
        return {"message": f"Visage de {name} enregistré avec succès !"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.post("/verify")
async def verify_face(payload: VerifyPayload):
    try:
        embeddings = load_all_embeddings()
        if not embeddings:
            log_access_attempt(
                person_name="Inconnu",
                status=ACCESS_DENIED_STATUS,
                note="Tentative de verification sans personne enregistree.",
            )
            return JSONResponse(status_code=400, content={"message": "Aucun visage n'est enregistré. Veuillez enregistrer quelqu'un d'abord."})

        img = process_base64_image(payload.image)
        faces = face_app.get(img)
        
        if len(faces) == 0:
            log_access_attempt(
                person_name="Inconnu",
                status=ACCESS_DENIED_STATUS,
                note="Aucun visage detecte devant la camera.",
            )
            return JSONResponse(status_code=400, content={"message": "Aucun visage détecté devant la caméra."})
        
        # Compare against all registered faces
        face_emb = faces[0].normed_embedding
        best_sim = -1
        best_name = None
        
        for name, reg_emb in embeddings.items():
            sim = float(np.dot(face_emb, reg_emb))
            if sim > best_sim:
                best_sim = sim
                best_name = name
        
        if best_sim > 0.5:
            barrier_opened = send_arduino_command("OPEN")
            log_access_attempt(
                person_name=best_name,
                status=ACCESS_GRANTED_STATUS,
                similarity=best_sim,
                barrier_opened=barrier_opened,
                note="Acces accorde apres reconnaissance faciale.",
            )
            return {
                "status": "success",
                "similarity": best_sim,
                "name": best_name,
                "barrier_opened": barrier_opened,
                "message": f"ACCÈS ACCORDÉ — Bienvenue {best_name}"
            }
        else:
            log_access_attempt(
                person_name=best_name or "Inconnu",
                status=ACCESS_DENIED_STATUS,
                similarity=best_sim,
                note="Visage non reconnu ou seuil de similarite insuffisant.",
            )
            return {
                "status": "fail",
                "similarity": best_sim,
                "name": best_name,
                "barrier_opened": False,
                "message": "ACCÈS REFUSÉ — Personne non reconnue"
            }
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
