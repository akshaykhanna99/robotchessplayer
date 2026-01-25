// PCA9686 servo test over serial
// Serial format: "channel angle" (e.g., "0 90")

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Typical min/max pulse lengths for servos (adjust if needed)
// 12-bit values at 50Hz
const uint16_t SERVOMIN = 150;
const uint16_t SERVOMAX = 600;

const uint8_t SERVO_FREQ = 50; // 50 Hz for analog servos

uint16_t angleToPulse(uint8_t angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { }

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);

  Serial.println("PCA9686 servo control ready");
  Serial.println("Send: <channel> <angle>  (e.g., '0 90')");
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
      Serial.println("Invalid format. Use: <channel> <angle>");
      return;
    }

    int channel = line.substring(0, spaceIndex).toInt();
    int angle = line.substring(spaceIndex + 1).toInt();

    if (channel < 0 || channel > 15) {
      Serial.println("Channel out of range (0-15)");
      return;
    }

    uint16_t pulse = angleToPulse((uint8_t)angle);
    pwm.setPWM(channel, 0, pulse);

    Serial.print("CH ");
    Serial.print(channel);
    Serial.print(" -> ");
    Serial.print(angle);
    Serial.print(" deg (pulse ");
    Serial.print(pulse);
    Serial.println(")");
  }
}
