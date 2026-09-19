// ============================================================================
// panic-sensor plush firmware  (ESP32 + 2 ear servos + heartbeat motor)
//
// The plush is an ACTUATOR: it subscribes to the brain's "plush state" and
// expresses it -- ears mirror arousal, a chest motor beats like a heart that
// slows to lead the user down. Same "one contract" idea as the wristband.
//
//   BLE service  9a0b1001-...
//     STATE char 9a0b1002-...  WRITE <- 4 bytes:
//        [ mode(0=calm,1=rising,2=breathing,3=settling),
//          heartbeat_bpm,
//          breathe_phase(0=in,1=out),
//          secs ]
//
// STATUS: UNTESTED. No hardware yet -- written to the contract, pins are
// EXAMPLES, expect to tune on the bench. Verify wiring before power-on.
//
// Arduino IDE: Board = "ESP32 Dev Module". Install the "ESP32Servo" library.
// ============================================================================

#include <ESP32Servo.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ---- pins (EXAMPLES) --------------------------------------------------------
static const int PIN_EAR_L    = 18;
static const int PIN_EAR_R    = 19;
static const int PIN_HEART    = 25;   // vibration motor via transistor
static const int HEART_CH     = 0;    // LEDC channel

// ---- ear positions (degrees; tune to your linkage) -------------------------
static const int EAR_RELAXED = 40;
static const int EAR_PERKED  = 130;

#define SVC_UUID   "9a0b1001-1e3c-4f5a-9b2d-8c7e6f5a4b3c"
#define STATE_UUID "9a0b1002-1e3c-4f5a-9b2d-8c7e6f5a4b3c"

Servo earL, earR;

// ---- state (written over BLE) ----------------------------------------------
volatile uint8_t mode = 0;         // 0 calm, 1 rising, 2 breathing, 3 settling
volatile uint8_t heartBpm = 60;

// ---- animation bookkeeping --------------------------------------------------
uint32_t lastBeatMs = 0;
uint32_t beatBuzzUntil = 0;
float    earPos = EAR_RELAXED;     // current smoothed ear angle
uint32_t breathStartMs = 0;

class StateCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* c) override {
    std::string v = c->getValue();
    if (v.size() >= 1) mode = (uint8_t)v[0];
    if (v.size() >= 2 && (uint8_t)v[1] > 0) heartBpm = (uint8_t)v[1];
    if (mode == 2) breathStartMs = millis();   // (re)start breathing cycle
  }
};

void setup() {
  earL.attach(PIN_EAR_L);
  earR.attach(PIN_EAR_R);
  ledcSetup(HEART_CH, 20000, 8);
  ledcAttachPin(PIN_HEART, HEART_CH);
  ledcWrite(HEART_CH, 0);

  BLEDevice::init("panic-plush");
  BLEServer* server = BLEDevice::createServer();
  BLEService* svc = server->createService(SVC_UUID);
  BLECharacteristic* stateChar = svc->createCharacteristic(
      STATE_UUID, BLECharacteristic::PROPERTY_WRITE);
  stateChar->setCallbacks(new StateCallbacks());
  svc->start();
  BLEAdvertising* adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SVC_UUID);
  adv->start();
}

// heartbeat: a short buzz at the top of each beat; interval from heartBpm
void updateHeart() {
  uint32_t now = millis();
  uint32_t interval = 60000UL / (heartBpm ? heartBpm : 60);
  if (now - lastBeatMs >= interval) {
    lastBeatMs = now;
    beatBuzzUntil = now + 80;          // 80ms "lub"
  }
  ledcWrite(HEART_CH, (now < beatBuzzUntil) ? 160 : 0);
}

// ears: smoothly approach a target that depends on mode
void updateEars() {
  float target;
  switch (mode) {
    case 1: target = EAR_PERKED; break;                       // rising: perk up
    case 2: {                                                 // breathing: slow rise/fall
      float t = ((millis() - breathStartMs) % 10000) / 10000.0f;  // ~10s cycle
      float s = 0.5f * (1.0f - cosf(2.0f * 3.14159f * t));   // 0..1..0
      target = EAR_RELAXED + s * (EAR_PERKED - EAR_RELAXED) * 0.6f;
      break;
    }
    case 3: target = EAR_RELAXED + 15; break;                 // settling: easing back
    default: target = EAR_RELAXED; break;                     // calm
  }
  earPos += (target - earPos) * 0.08f;                        // smoothing
  int a = (int)earPos;
  earL.write(a);
  earR.write(180 - a);                                        // mirrored mount
}

void loop() {
  updateHeart();
  updateEars();
  delay(15);
}
