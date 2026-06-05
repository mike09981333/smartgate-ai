# Système de Reconnaissance Faciale et Barrière Automatique (Arduino)

Ce projet est une application complète permettant de contrôler l'accès physique à travers une barrière automatisée, en utilisant la reconnaissance faciale de pointe. 

L'application web a été construite avec **FastAPI** et s'appuie sur le modèle d'intelligence artificielle **InsightFace** pour une détection et une vérification faciale très précises. Lorsqu'un visage enregistré est reconnu, un signal est envoyé via port série à une carte **Arduino**, qui actionne un servomoteur pour ouvrir la barrière.

## Fonctionnalités Principales

- **Enregistrement de visages** : Ajoutez facilement de nouveaux utilisateurs autorisés via une interface web (capture par webcam).
- **Vérification d'accès** : L'interface scanne le visage devant la caméra et le compare avec la base de données.
- **Contrôle Matériel** : Communication série avec un Arduino pour déclencher l'ouverture physique d'une barrière (servomoteur).
- **Interface d'administration** : Visualisez et supprimez les visages autorisés depuis l'interface web.

## Structure du Projet

- `web_app/` : Contient l'application web FastAPI (backend), l'interface web HTML/CSS/JS (dans `static/`), et la base de données des visages enregistrés (dans `data/`).
- `arduino_barriere/` : Contient le code C++ (sketch `.ino`) à téléverser sur la carte Arduino.
- `webcam_recognition.py` / `test_recognition.py` : Scripts de test indépendants pour utiliser InsightFace directement.
- `EXECUTION_PROJET.md` : Guide d'installation et de lancement détaillé du projet.

## Installation et Utilisation

Pour un guide étape par étape sur la façon de configurer l'Arduino, d'installer les dépendances Python et de démarrer le serveur web, veuillez consulter le fichier **[EXECUTION_PROJET.md](EXECUTION_PROJET.md)**.

### Démarrage rapide du serveur :

Une fois l'environnement virtuel (`venv`) configuré et activé :
```bash
python3 -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```
L'interface sera alors accessible à l'adresse http://127.0.0.1:8000.

---
*Ce projet utilise les bibliothèques open-source [InsightFace](https://github.com/deepinsight/insightface), OpenCV et FastAPI.*
