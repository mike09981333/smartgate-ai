import os
import time
import glob
import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
from insightface.app import FaceAnalysis

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
ARDUINO_BAUDRATE = int(os.getenv("ARDUINO_BAUDRATE", "9600"))
ARDUINO_PORT = os.getenv("ARDUINO_PORT")
ARDUINO_ENABLED = os.getenv("ARDUINO_ENABLED", "1") != "0"
ARDUINO_READY_DELAY = float(os.getenv("ARDUINO_READY_DELAY", "2"))

# Create data directories on startup
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

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

# In-memory storage for registered face (persisted to a file)
REGISTERED_FACE_FILE = "registered_face.npy"
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
            return JSONResponse(status_code=400, content={"message": "Aucun visage n'est enregistré. Veuillez enregistrer quelqu'un d'abord."})

        img = process_base64_image(payload.image)
        faces = face_app.get(img)
        
        if len(faces) == 0:
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
            return {
                "status": "success",
                "similarity": best_sim,
                "name": best_name,
                "barrier_opened": barrier_opened,
                "message": f"ACCÈS ACCORDÉ — Bienvenue {best_name}"
            }
        else:
            return {
                "status": "fail",
                "similarity": best_sim,
                "barrier_opened": False,
                "message": "ACCÈS REFUSÉ — Personne non reconnue"
            }
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
