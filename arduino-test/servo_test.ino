#include <Servo.h>

Servo gripperServo;
const int SERVO_PIN = 9;

const int OPEN_ANGLE = 10;
const int CLOSE_ANGLE = 170;
const int STEP_DELAY = 15;  // ms between each degree

void setup() {
  Serial.begin(9600);
  gripperServo.attach(SERVO_PIN);
  gripperServo.write(OPEN_ANGLE);
  Serial.println("Gripper servo test ready");
  Serial.println("Send 'o' to open, 'c' to close, or 0-180 for exact angle");
  delay(1000);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "o") {
      smoothMove(OPEN_ANGLE);
      Serial.println("Opened");
    } 
    else if (input == "c") {
      smoothMove(CLOSE_ANGLE);
      Serial.println("Closed");
    } 
    else {
      int angle = input.toInt();
      if (angle >= 0 && angle <= 180) {
        smoothMove(angle);
        Serial.print("Moved to ");
        Serial.println(angle);
      }
    }
  }

  // Auto demo: open and close every 3 seconds
  static unsigned long lastMove = 0;
  static bool isOpen = true;
  
  if (millis() - lastMove > 3000) {
    if (isOpen) {
      smoothMove(CLOSE_ANGLE);
      Serial.println("Auto: Closing");
    } else {
      smoothMove(OPEN_ANGLE);
      Serial.println("Auto: Opening");
    }
    isOpen = !isOpen;
    lastMove = millis();
  }
}

void smoothMove(int targetAngle) {
  int currentAngle = gripperServo.read();
  int step = (targetAngle > currentAngle) ? 1 : -1;
  
  for (int a = currentAngle; a != targetAngle; a += step) {
    gripperServo.write(a);
    delay(STEP_DELAY);
  }
  gripperServo.write(targetAngle);
}
