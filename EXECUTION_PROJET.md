# Instructions d'execution du projet

Ce guide explique comment lancer l'interface web de reconnaissance faciale et connecter l'Arduino pour ouvrir la barriere quand un visage autorise est reconnu.

## 1. Preparer l'Arduino

1. Ouvrir le fichier Arduino :

   ```text
   arduino_barriere/arduino_barriere.ino
   ```

2. Televerser le sketch sur la carte Arduino depuis l'IDE Arduino.

3. Brancher le servo moteur sur la broche definie dans le code :

   ```cpp
   const int SERVO_PIN = 9;
   ```

4. Brancher l'Arduino au PC par USB.

Le code Arduino attend les commandes serie :

```text
OPEN
CLOSE
```

Quand Python envoie `OPEN`, la barriere s'ouvre, attend 3 secondes, puis se referme.

## 2. Se placer a la racine du projet

Toujours lancer les commandes depuis la racine :

```bash
cd ~/Documents/projets/insightface-master
```

Ne pas lancer `uvicorn` depuis `web-demos/`, sinon Python ne trouve pas le module `web_app`.

## 3. Creer et activer l'environnement virtuel

Si le dossier `venv` n'existe pas encore :

**Sous Linux/macOS :**
```bash
python3 -m venv venv
```

**Sous Windows :**
```cmd
python -m venv venv
```

Activer l'environnement virtuel :

**Sous Linux/macOS :**
```bash
source venv/bin/activate
```

**Sous Windows :**
```cmd
venv\Scripts\activate
```

Le terminal doit afficher quelque chose comme :

```bash
(venv) credo@envyX360:~/Documents/projets/insightface-master$
```

## 4. Installer les dependances

Avec le venv active :

```bash
pip install -r requirements.txt
```

Le projet charge automatiquement les variables depuis le fichier `.env`.
Si besoin, dupliquer d'abord l'exemple :

```bash
cp .env.exemple .env
```

Si `cv2` manque encore :

```bash
pip install opencv-python
```

Si `serial` manque :

```bash
pip install pyserial
```

## 5. Verifier le port Arduino

**Sous Linux/macOS :**
Brancher l'Arduino, puis executer :

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Les ports les plus courants sont :

```text
/dev/ttyACM0
/dev/ttyUSB0
```

**Sous Windows :**
Ouvrir le **Gestionnaire de périphériques** (Device Manager) et regarder dans la section **Ports (COM et LPT)**.
Les ports les plus courants sont `COM3`, `COM4`, etc.

Le projet essaie de detecter automatiquement ces ports. Si besoin, forcer le port avec `ARDUINO_PORT`.

## 6. Lancer l'interface web

Depuis la racine du projet :

**Sous Linux/macOS :**
```bash
python3 -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

**Sous Windows :**
```cmd
python -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

Si tu veux forcer le port Arduino :

**Sous Linux/macOS :**
```bash
ARDUINO_PORT=/dev/ttyACM0 python3 -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

**Sous Windows (CMD) :**
```cmd
set ARDUINO_PORT=COM3 && python -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

**Sous Windows (PowerShell) :**
```powershell
$env:ARDUINO_PORT="COM3"; python -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

## 7. Ouvrir l'application

Dans le navigateur :

```text
http://127.0.0.1:8000
```

## 8. Utilisation

1. Aller dans l'onglet d'enregistrement.
2. Entrer le nom de la personne.
3. Capturer le visage pour l'enregistrer.
4. Aller dans l'onglet de verification.
5. Capturer le visage.
6. Si le visage correspond, l'API renvoie `success` et envoie `OPEN` a l'Arduino.
7. La barriere s'ouvre automatiquement.

## 8.b Base de donnees SQLite

Une base SQLite est creee automatiquement dans :

```text
web_app/data/smartgate.db
```

La table `access_logs` enregistre chaque tentative avec :

- le nom de la personne
- le statut `accorde` ou `refuse`
- le score de similarite
- la date
- l'heure
- le jour
- l'horodatage complet
- l'etat d'ouverture de la barriere
- une note descriptive

Tu peux aussi consulter l'historique via l'API :

```text
GET /access-logs
```

## 9. Probleme de permission Arduino

Si Python detecte l'Arduino mais n'a pas le droit d'ouvrir le port serie, executer :

```bash
sudo usermod -a -G dialout $USER
```

Ensuite, fermer la session Linux puis se reconnecter.

Verifier les groupes :

```bash
groups
```

Le groupe `dialout` doit apparaitre.

## 10. Erreurs courantes

### `ModuleNotFoundError: No module named 'web_app'`

Tu n'es pas dans la racine du projet.

Correction :

```bash
cd ~/Documents/projets/insightface-master
python3 -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

### `ModuleNotFoundError: No module named 'cv2'`

OpenCV n'est pas installe dans le venv.

Correction :

```bash
source venv/bin/activate
pip install opencv-python
```

### `Arduino introuvable`

Verifier que l'Arduino est branche :

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Puis relancer avec le bon port :

```bash
ARDUINO_PORT=/dev/ttyACM0 python3 -m uvicorn web_app.main:app --host 127.0.0.1 --port 8000
```

### La barriere ne bouge pas alors que l'acces est accorde

Verifier dans cet ordre :

1. Le sketch Arduino est bien televerse.
2. Le servo est branche sur la broche 9.
3. L'Arduino est branche en USB.
4. Le port serie est correct.
5. Le terminal affiche `Commande Arduino envoyee: OPEN`.

## 11. Arreter le serveur

Dans le terminal ou `uvicorn` tourne :

```bash
Ctrl + C
```
