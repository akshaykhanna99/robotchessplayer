// PCA9686 servo control over serial
// Serial format:
//   PCA <channel> <angle>   (e.g., "PCA 0 90")

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const uint16_t SERVOMIN = 150;
const uint16_t SERVOMAX = 600;
const uint8_t SERVO_FREQ = 50;

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
  Serial.println("PCA <channel> <angle>  (e.g., 'PCA 0 90')");
  Serial.println("Multiple PCA channels are supported.");
}

void handlePca(int channel, int angle) {
  if (channel < 0 || channel > 15) {
    Serial.println("PCA channel out of range (0-15)");
    return;
  }
  uint16_t pulse = angleToPulse((uint8_t)angle);
  pwm.setPWM(channel, 0, pulse);
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      return;
    }

    int firstSpace = line.indexOf(' ');
    if (firstSpace < 0) {
      Serial.println("Invalid format");
      return;
    }

    String prefix = line.substring(0, firstSpace);
    String rest = line.substring(firstSpace + 1);
    rest.trim();

    int secondSpace = rest.indexOf(' ');
    if (secondSpace < 0) {
      Serial.println("Invalid format");
      return;
    }

    int value1 = rest.substring(0, secondSpace).toInt();
    int value2 = rest.substring(secondSpace + 1).toInt();

    prefix.toUpperCase();
    if (prefix == "PCA") {
      handlePca(value1, value2);
    } else {
      Serial.println("Unknown prefix (use PCA)");
    }
  }
}
