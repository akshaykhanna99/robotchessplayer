// Gripper calibration tool for a PCA9686-driven servo.
//
// Upload this sketch, open Serial Monitor at 115200 baud, and send commands:
//   ?              -> print help and current state
//   s              -> print current state
//   +              -> increase pulse by 5
//   -              -> decrease pulse by 5
//   ++             -> increase pulse by 20
//   --             -> decrease pulse by 20
//   p <value>      -> set raw PCA9686 pulse directly (150-600 typical)
//   a <angle>      -> set servo angle in degrees (0-180)
//   c <channel>    -> change PCA9686 channel
//
// Use this to find the pulse values for fully open and fully closed positions.

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const uint16_t SERVOMIN = 150;
const uint16_t SERVOMAX = 600;
const uint8_t SERVO_FREQ = 50;

uint8_t currentChannel = 4;
uint16_t currentPulse = 450;

uint16_t angleToPulse(int angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

int pulseToAngle(uint16_t pulse) {
  pulse = constrain(pulse, SERVOMIN, SERVOMAX);
  return map(pulse, SERVOMIN, SERVOMAX, 0, 180);
}

void applyPulse() {
  pwm.setPWM(currentChannel, 0, currentPulse);
}

void printState() {
  Serial.print("Channel: ");
  Serial.print(currentChannel);
  Serial.print(" | Pulse: ");
  Serial.print(currentPulse);
  Serial.print(" | Approx angle: ");
  Serial.println(pulseToAngle(currentPulse));
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  ?        help");
  Serial.println("  s        show current state");
  Serial.println("  + / -    step pulse by 5");
  Serial.println("  ++ / --  step pulse by 20");
  Serial.println("  p <n>    set pulse directly");
  Serial.println("  a <n>    set angle directly");
  Serial.println("  c <n>    set PCA9686 channel");
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { }

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);

  applyPulse();

  Serial.println("Gripper calibration ready");
  printHelp();
  printState();
}

void loop() {
  if (Serial.available() <= 0) {
    return;
  }

  String line = Serial.readStringUntil('\n');
  line.trim();

  if (line.length() == 0) {
    return;
  }

  if (line == "?" || line == "help") {
    printHelp();
    printState();
    return;
  }

  if (line == "s") {
    printState();
    return;
  }

  if (line == "+") {
    currentPulse = constrain(currentPulse + 5, SERVOMIN, SERVOMAX);
    applyPulse();
    printState();
    return;
  }

  if (line == "-") {
    currentPulse = constrain(currentPulse - 5, SERVOMIN, SERVOMAX);
    applyPulse();
    printState();
    return;
  }

  if (line == "++") {
    currentPulse = constrain(currentPulse + 20, SERVOMIN, SERVOMAX);
    applyPulse();
    printState();
    return;
  }

  if (line == "--") {
    currentPulse = constrain(currentPulse - 20, SERVOMIN, SERVOMAX);
    applyPulse();
    printState();
    return;
  }

  int spaceIndex = line.indexOf(' ');
  if (spaceIndex < 0) {
    Serial.println("Invalid command");
    return;
  }

  String command = line.substring(0, spaceIndex);
  int value = line.substring(spaceIndex + 1).toInt();

  if (command == "p") {
    currentPulse = constrain(value, SERVOMIN, SERVOMAX);
    applyPulse();
    printState();
    return;
  }

  if (command == "a") {
    currentPulse = angleToPulse(value);
    applyPulse();
    printState();
    return;
  }

  if (command == "c") {
    currentChannel = constrain(value, 0, 15);
    applyPulse();
    printState();
    return;
  }

  Serial.println("Unknown command");
}
