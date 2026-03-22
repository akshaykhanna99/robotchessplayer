// Full robot serial control for PCA9686.
//
// Protocol expected by robot_mech_testing/full_robot_test_run.py:
//   <channel>,<pulse>
// Example:
//   0,375
//   4,180
//
// Additional commands:
//   STATUS          Print all current channel pulse values
//   RESET           Move all servos to their startup defaults
//   HELP            Print command help

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver(0x40);

const uint8_t NUM_SERVOS = 5;
const uint8_t SERIAL_BUFFER_SIZE = 48;
const uint8_t SERVO_FREQ = 50;

char inputBuffer[SERIAL_BUFFER_SIZE];
uint8_t inputLength = 0;

// Startup defaults tuned for the current mechanism.
int servoPulse[NUM_SERVOS] = {
  375,  // base
  375,  // shoulder
  385,  // elbow
  375,  // wrist
  340   // gripper open
};

const int servoDefault[NUM_SERVOS] = {
  375,  // base
  375,  // shoulder
  385,  // elbow
  375,  // wrist
  340   // gripper open
};

const int servoMin[NUM_SERVOS] = {
  250,  // base
  250,  // shoulder
  250,  // elbow
  250,  // wrist
  180   // gripper closed
};

const int servoMax[NUM_SERVOS] = {
  500,  // base
  500,  // shoulder
  500,  // elbow
  500,  // wrist
  340   // gripper open
};

bool parseIntStrict(const String &text, int &value) {
  if (text.length() == 0) {
    return false;
  }

  uint8_t start = 0;
  if (text[0] == '-' || text[0] == '+') {
    if (text.length() == 1) {
      return false;
    }
    start = 1;
  }

  for (uint8_t i = start; i < text.length(); ++i) {
    if (!isDigit(text[i])) {
      return false;
    }
  }

  value = text.toInt();
  return true;
}

void printHelp() {
  Serial.println("READY");
  Serial.println("Commands:");
  Serial.println("  <channel>,<pulse>  set servo pulse");
  Serial.println("  STATUS             print all pulse values");
  Serial.println("  RESET              restore startup defaults");
  Serial.println("  HELP               show this help");
}

void printStatus() {
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    Serial.print("CH ");
    Serial.print(i);
    Serial.print(" = ");
    Serial.println(servoPulse[i]);
  }
}

void applyServo(uint8_t channel, int pulse) {
  int boundedPulse = constrain(pulse, servoMin[channel], servoMax[channel]);
  servoPulse[channel] = boundedPulse;
  pca.setPWM(channel, 0, boundedPulse);
}

void resetAllServos() {
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    applyServo(i, servoDefault[i]);
    delay(120);
  }
}

void processServoCommand(const String &command) {
  int commaIndex = command.indexOf(',');
  if (commaIndex <= 0 || commaIndex >= command.length() - 1) {
    Serial.println("ERR invalid format, expected channel,pulse");
    return;
  }

  String channelText = command.substring(0, commaIndex);
  String pulseText = command.substring(commaIndex + 1);
  channelText.trim();
  pulseText.trim();

  int channel = 0;
  int pulse = 0;
  if (!parseIntStrict(channelText, channel) || !parseIntStrict(pulseText, pulse)) {
    Serial.println("ERR invalid integer");
    return;
  }

  if (channel < 0 || channel >= NUM_SERVOS) {
    Serial.println("ERR channel out of range");
    return;
  }

  applyServo((uint8_t)channel, pulse);

  Serial.print("OK CH ");
  Serial.print(channel);
  Serial.print(" = ");
  Serial.println(servoPulse[channel]);
}

void processCommand(const String &rawCommand) {
  String command = rawCommand;
  command.trim();
  if (command.length() == 0) {
    return;
  }

  String upperCommand = command;
  upperCommand.toUpperCase();

  if (upperCommand == "HELP") {
    printHelp();
    return;
  }

  if (upperCommand == "STATUS") {
    printStatus();
    return;
  }

  if (upperCommand == "RESET") {
    resetAllServos();
    Serial.println("OK reset");
    printStatus();
    return;
  }

  processServoCommand(command);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { }

  pca.begin();
  pca.setPWMFreq(SERVO_FREQ);
  delay(500);

  resetAllServos();
  printHelp();
  printStatus();
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      inputBuffer[inputLength] = '\0';
      processCommand(String(inputBuffer));
      inputLength = 0;
      continue;
    }

    if (inputLength >= SERIAL_BUFFER_SIZE - 1) {
      inputLength = 0;
      Serial.println("ERR command too long");
      continue;
    }

    inputBuffer[inputLength++] = c;
  }
}
