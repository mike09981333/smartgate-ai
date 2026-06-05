#include <Servo.h>

Servo barriere;

const int SERVO_PIN = 9;
const int FERME = 90;
const int OUVERT = 0;

void setup() {
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "OPEN") {
      ouvrirBarriere();
    } else if (cmd == "CLOSE") {
      fermerBarriere();
    }
  }
}

void ouvrirBarriere() {
  barriere.attach(SERVO_PIN);
  barriere.write(OUVERT);
  delay(5000);
  barriere.write(FERME);
  delay(500);
  barriere.detach();
}

void fermerBarriere() {
  barriere.attach(SERVO_PIN);
  barriere.write(FERME);
  delay(500);
  barriere.detach();
}
