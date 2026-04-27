#include <Arduino.h>
#include <ESP32Servo.h>
#include <Adafruit_NeoPixel.h>

// --- NeoPixel Configuration ---
#define PIN_1 4
#define PIN_2 5
#define N_LEDS 60
#define BRIGHTNESS 200 // 40% brightness

// --- Servo Configuration ---
const int servoPin1 = 19;
const int servoPin2 = 18;

// Instantiate Objects
Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(N_LEDS, PIN_1, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(N_LEDS, PIN_2, NEO_GRB + NEO_KHZ800);
Servo servo1;
Servo servo2;

void setup() {
  Serial.begin(115200);
  
  // NeoPixels algseadistus
  strip1.begin();
  strip2.begin();
  strip1.setBrightness(BRIGHTNESS);
  strip2.setBrightness(BRIGHTNESS);
  
  // Lülitame alguses ootevärvi peale (sinakas-roheline)
  setLEDs(107, 202, 186);

  // Servode algseadistus
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  
  // Hoiame servod alguses lahti ühendatuna, et vältida surisemist
  // Kinnitame nad alles siis, kui liikumine reaalselt algab.
  Serial.println("ESP32 VALMIS. Ootan käsklusi...");
}

void loop() {
  // Kuulame, kas Raspberry Pi saatis meile USB kaudu sõnumi
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // Eemaldame tühikud ja reavahetused

    if (cmd == "DISPENSE") {
      runDispenseCycle();
    } 
    else if (cmd == "LED_WIN") {
      setLEDs(0, 255, 0); // Roheline võiduvärv
    }
    else if (cmd == "LED_IDLE") {
      setLEDs(107, 202, 186); // Algne ootevärv
    }
    else if (cmd == "LED_OFF") {
      setLEDs(0, 0, 0); // Tuled kustu
    }
  }
}

// --- ABIFUNKTSIOONID ---

void setLEDs(int r, int g, int b) {
  strip1.fill(strip1.Color(r, g, b));
  strip2.fill(strip2.Color(r, g, b));
  strip1.show();
  strip2.show();
}

void runDispenseCycle() {
  Serial.println("Alustan väljastustsüklit!");
  
  // Ühendame servod uuesti külge
  servo1.attach(servoPin1, 570, 2465);
  servo2.attach(servoPin2, 570, 2465);
  
  // Turvaline algasend
  servo1.write(0);
  servo2.write(0);
  delay(1000);

  // Tsükkel
  servo1.write(180);
  delay(2000);

  servo2.write(180);
  delay(2000);

  servo2.write(0);
  delay(2000);

  servo1.write(0);
  delay(2000); // Ootab füüsilise liikumise lõppu

  // Vabastame servod (Jitteri tapja)
  servo1.detach();
  servo2.detach();
  
  Serial.println("Väljastustsükkel lõpetatud!"); // Pi ootab seda vastust!
}
