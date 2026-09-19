// ============================================================================
// panic-sensor wristband firmware  (ESP32 + MPU6050 + coin/LRA haptic)
//
// Streams accelerometer over BLE and buzzes a paced-breathing rhythm on command.
// Speaks the SAME contract as ble_bridge.py, so it drops into the existing
// pipeline with no changes on the laptop side.
//
//   BLE service  9a0b0001-...
//     ACCEL char 9a0b0002-...  NOTIFY  -> N samples x int16(ax,ay,az) LE, milli-g
//     BREATHE ch 9a0b0003-...  WRITE   <- 3 bytes [action(0/1), inhale_s, exhale_s]
//
// STATUS: UNTESTED. Written against the datasheets and the contract; we don't
// have the ESP32 yet, so it has never run on hardware. Pin numbers are EXAMPLES.
// Verify wiring before power-on (claude-code-eyes is handy here), and expect to
// debug on the bench.
//
// Arduino IDE: Board = "ESP32 Dev Module". Uses the built-in ESP32 BLE stack
// (BLEDevice.h) and Wire; no external libraries required (MPU6050 is read via
// raw I2C registers to keep dependencies at zero).
// ============================================================================

#include <Arduino.h>
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ---- pins (EXAMPLES -- change to your wiring) -------------------------------
static const int PIN_SDA     = 21;
static const int PIN_SCL     = 22;
static const int PIN_HAPTIC  = 25;   // -> transistor base/gate driving the motor
static const int HAPTIC_CH   = 0;    // LEDC channel

// ---- MPU6050 ----------------------------------------------------------------
static const uint8_t MPU_ADDR = 0x68;
static const float    LSB_PER_G = 16384.0f;  // +/-2g full scale

// ---- sampling / packetization ----------------------------------------------
static const int      SAMPLE_HZ = 50;
static const uint32_t SAMPLE_US = 1000000UL / SAMPLE_HZ;
static const int      SAMPLES_PER_PACKET = 4;  // 4 * 3 * int16 = 24 bytes/notify

// ---- BLE UUIDs (must match ble_bridge.py) ----------------------------------
#define SVC_UUID     "9a0b0001-1e3c-4f5a-9b2d-8c7e6f5a4b3c"
#define ACCEL_UUID   "9a0b0002-1e3c-4f5a-9b2d-8c7e6f5a4b3c"
#define BREATHE_UUID "9a0b0003-1e3c-4f5a-9b2d-8c7e6f5a4b3c"

BLECharacteristic* accelChar = nullptr;
volatile bool deviceConnected = false;

// ---- breathing (paced haptic) state ----------------------------------------
volatile bool  breatheOn = false;
volatile uint8_t inhaleS = 4, exhaleS = 6;
uint32_t phaseStartMs = 0;
bool     exhaling = false;

// ---- sample buffer ----------------------------------------------------------
int16_t  pktBuf[SAMPLES_PER_PACKET * 3];
int      pktCount = 0;
uint32_t lastSampleUs = 0;

void mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg); Wire.write(val);
  Wire.endTransmission();
}

void readAccel(int16_t& ax, int16_t& ay, int16_t& az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);                       // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom((int)MPU_ADDR, 6, (int)true);
  ax = (Wire.read() << 8) | Wire.read();
  ay = (Wire.read() << 8) | Wire.read();
  az = (Wire.read() << 8) | Wire.read();
}

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { deviceConnected = true; }
  void onDisconnect(BLEServer* s) override {
    deviceConnected = false;
    breatheOn = false;
    s->getAdvertising()->start();        // allow reconnect
  }
};

class BreatheCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* c) override {
    std::string v = c->getValue();
    if (v.size() < 1) return;
    breatheOn = (uint8_t)v[0] != 0;
    if (v.size() >= 3) { inhaleS = (uint8_t)v[1]; exhaleS = (uint8_t)v[2]; }
    phaseStartMs = millis();
    exhaling = false;                    // start on the inhale
    if (!breatheOn) ledcWrite(HAPTIC_CH, 0);
  }
};

void setup() {
  Wire.begin(PIN_SDA, PIN_SCL);
  mpuWrite(0x6B, 0x00);                  // PWR_MGMT_1: wake up
  delay(50);

  ledcSetup(HAPTIC_CH, 20000, 8);        // 20kHz, 8-bit
  ledcAttachPin(PIN_HAPTIC, HAPTIC_CH);
  ledcWrite(HAPTIC_CH, 0);

  BLEDevice::init("panic-wrist");
  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService* svc = server->createService(SVC_UUID);

  accelChar = svc->createCharacteristic(
      ACCEL_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  accelChar->addDescriptor(new BLE2902());

  BLECharacteristic* breatheChar = svc->createCharacteristic(
      BREATHE_UUID, BLECharacteristic::PROPERTY_WRITE);
  breatheChar->setCallbacks(new BreatheCallbacks());

  svc->start();
  BLEAdvertising* adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SVC_UUID);
  adv->start();

  lastSampleUs = micros();
}

// Non-blocking paced-breathing haptic: a gentle sustained buzz during the
// exhale (the cue to breathe out slowly), off during the inhale.
void updateHaptic() {
  if (!breatheOn) { ledcWrite(HAPTIC_CH, 0); return; }
  uint32_t now = millis();
  uint32_t phaseMs = (exhaling ? exhaleS : inhaleS) * 1000UL;
  if (now - phaseStartMs >= phaseMs) { exhaling = !exhaling; phaseStartMs = now; }
  ledcWrite(HAPTIC_CH, exhaling ? 120 : 0);   // ~47% duty during exhale
}

void loop() {
  uint32_t now = micros();
  if (now - lastSampleUs >= SAMPLE_US) {
    lastSampleUs += SAMPLE_US;
    int16_t ax, ay, az;
    readAccel(ax, ay, az);
    // raw LSB -> g -> milli-g int16 (fits: +/-2000 mg << 32767)
    pktBuf[pktCount * 3 + 0] = (int16_t)(ax / LSB_PER_G * 1000.0f);
    pktBuf[pktCount * 3 + 1] = (int16_t)(ay / LSB_PER_G * 1000.0f);
    pktBuf[pktCount * 3 + 2] = (int16_t)(az / LSB_PER_G * 1000.0f);
    pktCount++;
    if (pktCount >= SAMPLES_PER_PACKET) {
      if (deviceConnected && accelChar) {
        accelChar->setValue((uint8_t*)pktBuf, sizeof(int16_t) * 3 * pktCount);
        accelChar->notify();
      }
      pktCount = 0;
    }
  }
  updateHaptic();
}
