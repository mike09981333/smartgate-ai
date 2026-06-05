import cv2
import numpy as np
from insightface.app import FaceAnalysis

def main():
    print("Initialisation du modèle InsightFace...")
    # On utilise le CPU par défaut
    app = FaceAnalysis(providers=['CPUExecutionProvider'])
    # det_size est la taille de l'image sur laquelle le modèle va chercher les visages (réduit à 320 pour plus de fluidité)
    app.prepare(ctx_id=0, det_size=(320, 320))
    
    # Ouvrir la webcam (0 est généralement la webcam par défaut)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erreur: Impossible d'accéder à la webcam.")
        return

    reference_embedding = None
    print("\n" + "="*50)
    print("--- COMMANDES DE LA WEBCAM ---")
    print("[ S ] : ENREGISTRER votre visage (visage de référence)")
    print("[ R ] : RÉINITIALISER (effacer le visage enregistré)")
    print("[ Q ] : QUITTER l'application")
    print("="*50 + "\n")

    frame_count = 0
    faces = []

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur de lecture de la caméra.")
            break

        # On fait une copie de l'image pour dessiner dessus sans altérer l'image originale analysée
        display_frame = frame.copy()

        # Pour éviter le lag extrême sur CPU, on n'analyse l'image qu'une fois toutes les 3 frames (frame skipping)
        if frame_count % 3 == 0:
            faces = app.get(frame)
        frame_count += 1
        
        for face in faces:
            # Récupérer les coordonnées de la boîte englobante du visage
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            
            if reference_embedding is not None:
                # Si on a un visage de référence, on compare (produit scalaire = similarité cosinus)
                sim = np.dot(face.normed_embedding, reference_embedding)
                
                # Le seuil est souvent autour de 0.5
                if sim > 0.5:
                    color = (0, 255, 0) # Vert = Identifié
                    text = f"MOI ! ({sim:.2f})"
                else:
                    color = (0, 0, 255) # Rouge = Inconnu
                    text = f"Inconnu ({sim:.2f})"
            else:
                # Si pas de référence enregistrée, on dessine juste en bleu/cyan
                color = (255, 255, 0) 
                text = "Visage (Appuyez sur 's' pour sauver)"

            # Dessiner le rectangle et le texte
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Afficher les instructions en haut de l'écran
        if reference_embedding is None:
            cv2.putText(display_frame, "Appuyez sur 'S' pour enregistrer votre visage", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            cv2.putText(display_frame, "Mode actif (Q: quitter, R: reset)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Afficher la fenêtre vidéo
        cv2.imshow('Reconnaissance Faciale en direct', display_frame)

        # Gérer les touches du clavier
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if len(faces) == 1:
                # On enregistre le vecteur (embedding) du seul visage détecté
                reference_embedding = faces[0].normed_embedding
                print("✅ Visage de référence enregistré avec succès !")
            elif len(faces) == 0:
                print("❌ Aucun visage détecté. Veuillez bien vous placer devant la caméra.")
            else:
                print("❌ Plusieurs visages détectés. Veuillez être seul devant la caméra pour l'enregistrement.")
        elif key == ord('r'):
            reference_embedding = None
            print("🔄 Visage de référence réinitialisé.")

    # Libérer la caméra et fermer les fenêtres
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
