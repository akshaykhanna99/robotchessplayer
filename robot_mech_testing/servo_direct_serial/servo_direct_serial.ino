// Direct Arduino servo test over serial (no PCA9686)
// Serial format: "pin angle" (e.g., "9 90")

#include <Servo.h>

Servo servo;
int attachedPin = -1;

void setup() {
  Serial.begin(115200);
  while (!Serial) { }
  Serial.println("Direct servo control ready");
  Serial.println("Send: <pin> <angle>  (e.g., '9 90')");
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      return;
    }

    int spaceIndex = line.indexOf(' ');
    if (spaceIndex < 0) {
      Serial.println("Invalid format. Use: <pin> <angle>");
      return;
    }

    int pin = line.substring(0, spaceIndex).toInt();
    int angle = line.substring(spaceIndex + 1).toInt();

    if (pin < 2 || pin > 13) {
      Serial.println("Pin out of range (2-13)");
      return;
    }

    if (attachedPin != pin) {
      if (attachedPin != -1) {
        servo.detach();
      }
      servo.attach(pin);
      attachedPin = pin;
    }

    angle = constrain(angle, 0, 180);
    servo.write(angle);

    Serial.print("PIN ");
    Serial.print(pin);
    Serial.print(" -> ");
    Serial.print(angle);
    Serial.println(" deg");
  }
}
