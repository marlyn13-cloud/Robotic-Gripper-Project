#include <Servo.h>

Servo gripperServo;
const int SERVO_PIN = 9;
const int DEFAULT_ANGLE = 90;

int currentAngle = DEFAULT_ANGLE;
int targetAngle = DEFAULT_ANGLE;

void setup() {
  Serial.begin(9600);
  gripperServo.attach(SERVO_PIN);
  gripperServo.write(DEFAULT_ANGLE);
  Serial.println("READY");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    int angle = input.toInt();
    if (angle >= 0 && angle <= 180) {
      targetAngle = angle;
      gripperServo.write(targetAngle);
      currentAngle = targetAngle;
      Serial.print("OK:");
      Serial.println(currentAngle);
    }
  }
}
