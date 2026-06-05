import cv2
import urllib.request
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import os

# Create a directory to store images if not exists
os.makedirs('test_images', exist_ok=True)

# Helper function to download an image
def download_image(url, filename):
    filepath = os.path.join('test_images', filename)
    if not os.path.exists(filepath):
        print(f"Téléchargement de {filename}...")
        # Add user-agent to avoid 403 Forbidden on some websites
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
    return filepath

# URLs for test images
# Einstein 1
url_einstein_1 = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg/330px-Einstein_1921_by_F_Schmutzer_-_restoration.jpg"
# Einstein 2
url_einstein_2 = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Albert_Einstein_Head.jpg/330px-Albert_Einstein_Head.jpg"
# Newton
url_newton = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/GodfreyKneller-IsaacNewton-1689.jpg/330px-GodfreyKneller-IsaacNewton-1689.jpg"

path_e1 = download_image(url_einstein_1, 'einstein1.jpg')
path_e2 = download_image(url_einstein_2, 'einstein2.jpg')
path_n = download_image(url_newton, 'newton.jpg')

print("\n--- Initialisation du modèle InsightFace ---")
# Initialize the FaceAnalysis app for CPU
app = FaceAnalysis(providers=['CPUExecutionProvider'])
# The first time this is run, it will download the "buffalo_l" model (~300MB)
print("Préparation du modèle (téléchargement si nécessaire)...")
app.prepare(ctx_id=0, det_size=(640, 640))

# Helper function to get face embedding
def get_face_embedding(app, image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")
    
    faces = app.get(img)
    if len(faces) == 0:
        raise ValueError(f"Aucun visage détecté dans : {image_path}")
    
    # We assume the largest/most prominent face is the target
    # Insightface sorts faces. Usually the first one is the main one.
    return faces[0].normed_embedding, faces[0], img

print("\n--- Extraction des caractéristiques (Embeddings) ---")
emb_e1, face_e1, img_e1 = get_face_embedding(app, path_e1)
print(f"Einstein 1 extrait avec succès.")

emb_e2, face_e2, img_e2 = get_face_embedding(app, path_e2)
print(f"Einstein 2 extrait avec succès.")

emb_n, face_n, img_n = get_face_embedding(app, path_n)
print(f"Newton extrait avec succès.")

# Calculate similarities
# The embeddings are already L2-normalized, so the dot product gives the cosine similarity.
# Value ranges from -1 to 1. Usually > 0.5 or 0.6 means the same person in InsightFace buffalo_l.
def compute_similarity(emb1, emb2):
    return np.dot(emb1, emb2)

print("\n--- Résultats de la Comparaison Faciale ---")
sim_e1_e2 = compute_similarity(emb_e1, emb_e2)
print(f"1. Einstein 1 vs Einstein 2 : Similarité = {sim_e1_e2:.4f} -> {'MÊME PERSONNE' if sim_e1_e2 > 0.5 else 'PERSONNES DIFFÉRENTES'}")

sim_e1_n = compute_similarity(emb_e1, emb_n)
print(f"2. Einstein 1 vs Newton    : Similarité = {sim_e1_n:.4f} -> {'MÊME PERSONNE' if sim_e1_n > 0.5 else 'PERSONNES DIFFÉRENTES'}")

print("\n(Note: Une similarité supérieure à 0.5 indique généralement qu'il s'agit de la même personne)")
