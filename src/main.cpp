#include <Arduino.h>
#include <WiFi.h>

#include <LittleFS.h>
#include <ArduinoMqttClient.h>
#include <PMS.h>
#include <Adafruit_I2CDevice.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP085.h>
#include <Adafruit_SGP30.h>
#include <Wire.h>

#include "caqi.h"
#include "conf.h"
#include "utils.h"

#ifdef DEBUG
#define DEBUG_PRINT(x) Serial.println(x)
#else
#define DEBUG_PRINT(x)
#endif


// Forward declarations
void wifiConnect();
void pmsMeasure();
void ahtMeasure(TempData &temp_data);
void bmpMeasure(TempData &temp_data);
void sgpMeasure();
void sgpUpdateBaseline();
void sgpUpdateHumidity(TempData &temp_data);
inline void mqttPublish(const char *topic, int payload);
inline void mqttPublish(const char *topic, float payload, int precision);
inline void mqttPublish(const char *topic, const char *payload);


// Global objects
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

PMS pms(Serial1);

Adafruit_AHTX0 aht20;
Adafruit_BMP085 bmp180;
Adafruit_SGP30 sgp30;


void setup() {
    // Init USB Serial
#ifdef DEBUG
    Serial.begin(115200);
    delay(3000);
#endif
    Serial1.begin(9600);

    // Init WiFi
#ifdef ARDUINO_RASPBERRY_PI_PICO_W
    WiFi.defaultLowPowerMode();
#endif
    if (WiFi.status() == WL_CONNECTED) {
        DEBUG_PRINT("Disconnecting previous connection");
        WiFi.disconnect();
    }
    wifiConnect();

    // Init MQTT
    DEBUG_PRINT("Connecting to MQTT broker");
    mqttClient.setId(CLIENT_ID);
    mqttClient.setKeepAliveInterval(320); // 5 minutes
    while (!mqttClient.connect(BROKER, BROKER_PORT)) {
        DEBUG_PRINT("Retrying...");
        delay(5000);
    }
    DEBUG_PRINT("Connected!");

    DEBUG_PRINT("Preparing sensors");

    // Init PMS
    pms.passiveMode();
    pms.sleep();

    // Init AHT20
    if (aht20.begin() != true) {  // aht20.begin() initialize and calibrate the sensor
        DEBUG_PRINT("AHT20 begin failed");
        mqttPublish(topic_err, "AHT20 begin failed");
        delay(5000);
    }

    // Init BMP180
    if (bmp180.begin(BMP085_ULTRALOWPOWER) != true) {  // By using ULTRALOWPOWER with reduce the samples to 3
        DEBUG_PRINT("BMP180 begin failed");
        mqttPublish(topic_err, "BMP180 begin failed");
        delay(5000);
    }

    // Init SGP30
    if (sgp30.begin() != true) {  // sgp30.begin() initialize and calibrate the sensor
        DEBUG_PRINT("SGP30 begin failed");
        mqttPublish(topic_err, "SGP30 begin failed");
        delay(5000);
    }
    // Read from flash baselines if available
    if (LittleFS.begin()) {
        File file = LittleFS.open("/baseline.txt", "r");
        if (file) {
            DEBUG_PRINT("Baseline file found");
            uint16_t eco2, tvoc;
            tvoc = file.parseInt();
            eco2 = file.parseInt();
            sgp30.setIAQBaseline(eco2, tvoc);
            file.close();
        } else {
            DEBUG_PRINT("Failed to open baseline.txt");
        }
        LittleFS.end();
    } else {
        DEBUG_PRINT("Failed to mount FS");
        mqttPublish(topic_err, "Failed to mount FS");
    }

    // Ready
    DEBUG_PRINT("Ready!");
    lightsleep(30); // 30 seconds
}


void loop() {
    TempData data;

    if (WiFi.status() != WL_CONNECTED)
        wifiConnect();
    mqttClient.poll();

    // Read PMS data
    pmsMeasure();

    // Read BMP180 data
    bmpMeasure(data);

    // Read AHT20 data
    ahtMeasure(data);

    // Read SGP30 data
    sgpMeasure();
    sgpUpdateHumidity(data);
    sgpUpdateBaseline();

    lightsleep(60 * 5); // 4 minutes
}


void pmsMeasure() {
    // Static variables used for caqi calculation
    static int pm_counter = 0;
    static int pm10_sum = 0;
    static int pm25_sum = 0;
    static unsigned long last_measure_time = millis();

    // struct to store PMS data
    PMS::DATA data;

    // Read PMS data
    while (Serial1.available()) { Serial1.read(); }  // Clear serial buffer
    pms.wakeUp();
    lightsleep(40); // 40 seconds
    pms.requestRead(); Serial1.flush();
    if (!pms.readUntil(data, 5000)) {
        DEBUG_PRINT("PMS read failed");
        mqttPublish(topic_err, "PMS read failed");
        pms.sleep(); Serial1.flush();
        return;
    }
    pms.sleep(); Serial1.flush();

    // Increase counter for caqi calculation
    pm_counter++;
    pm10_sum += data.PM_AE_UG_10_0;
    pm25_sum += data.PM_AE_UG_2_5;

    // Check if it's time to calculate caqi and send data to MQTT broker
    if (millis() <= last_measure_time || millis() - last_measure_time >= 3600000) {  // measure every hour
        // Calculate CAQI
        int caqi = calculate_caqi(pm25_sum / pm_counter, pm10_sum / pm_counter);
        // Reset pm values
        last_measure_time = millis();
        pm_counter = 0;
        pm10_sum = 0;
        pm25_sum = 0;
        // Send CAQI to MQTT broker
        mqttPublish(topic_caqi, caqi);
    }

    // Send PMS data to MQTT broker
    mqttPublish(topic_pm01, data.PM_AE_UG_1_0);
    mqttPublish(topic_pm25, data.PM_AE_UG_2_5);
    mqttPublish(topic_pm100, data.PM_AE_UG_10_0);
}


void ahtMeasure(TempData &temp_data) {
    sensors_event_t temp, hum;
    if (!aht20.getEvent(&hum, &temp)) {
        DEBUG_PRINT("AHT20 getEvent failed");
        mqttPublish(topic_err, "AHT20 getEvent failed");
        return;
    };

    if (temp_data.temperature != 0) {
        // Average temperature with value from bmp180
        temp_data.temperature = (temp.temperature + temp_data.temperature) / 2;
    } else {
        temp_data.temperature = temp.temperature;
    }
    temp_data.humidity = hum.relative_humidity;

    // Send AHT20 data to MQTT broker
    mqttPublish(topic_temp, temp_data.temperature, 1);
    mqttPublish(topic_hum, temp_data.humidity, 0);
}


void bmpMeasure(TempData &temp_data) {
    int pressure = bmp180.readPressure();
    temp_data.temperature = bmp180.readTemperature();

    pressure = pressure - (pressure % 10);  // Round to nearest 10
    // Send BMP180 data to MQTT broker
    mqttPublish(topic_pres, pressure);
}


void sgpMeasure() {
    if (sgp30.IAQmeasureRaw()) {
        delay(50); // Wait for measurement to complete
        if (sgp30.IAQmeasure()) {
            mqttPublish(topic_tvoc, sgp30.TVOC);
            mqttPublish(topic_eco2, sgp30.eCO2);
        } else {
            DEBUG_PRINT("SGP30 IAQmeasure failed");
            mqttPublish(topic_err, "SGP30 IAQmeasure failed");
        }

        mqttPublish(topic_h2, sgp30.rawH2);
        mqttPublish(topic_ethanol, sgp30.rawEthanol);
    } else {
        DEBUG_PRINT("SGP30 IAQmeasureRaw failed");
        mqttPublish(topic_err, "SGP30 IAQmeasureRaw failed");
    }
}


void sgpUpdateBaseline() {
    static long next_baseline_update = 43200000;

    // Wait for 12 hours before saving the first baseline
    if (millis() <= next_baseline_update) {
        return;
    } else {
        // After the first baseline is saved, update it every hour
        next_baseline_update = millis() + 3600000;
    }

    // Read baseline from SGP30
    uint16_t eco2, tvoc;
    if (sgp30.getIAQBaseline(&eco2, &tvoc)) {
        // Write baseline to flash
        LittleFS.begin();
        File file = LittleFS.open("/baseline.txt", "w");
        if (file) {
            file.println(tvoc);
            file.println(eco2);
            file.close();
            DEBUG_PRINT("Baseline written to flash");
        } else {
            DEBUG_PRINT("Failed to write, baseline.txt");
            mqttPublish(topic_err, "Failed to write, baseline.txt");
        }
        LittleFS.end();
    }
}


void sgpUpdateHumidity(TempData &temp_data) {
    static long next_humidity_update = 0;

    // Update humidity every 6 hours
    if (millis() <= next_humidity_update) {
        return;
    } else {
        next_humidity_update = millis() + 21600000;
    }

    // Set abosulute humidity
    sgp30.setHumidity(getAbsoluteHumidity(temp_data.temperature, temp_data.humidity));
}


inline void mqttPublish(const char *topic, int payload) {
    if (!mqttClient.beginMessage(topic)) {
        DEBUG_PRINT("MQTT begin message failed");
        return;
    }

    #ifdef DEBUG
        Serial.print(topic);
        Serial.print(": ");
        Serial.println(payload);
    #endif
    mqttClient.print(payload);

    if (!mqttClient.endMessage())
        DEBUG_PRINT("MQTT end message failed");
}


inline void mqttPublish(const char *topic, float payload, int precision) {
    if (!mqttClient.beginMessage(topic)) {
        DEBUG_PRINT("MQTT begin message failed");
        return;
    }
    
    #ifdef DEBUG
        Serial.print(topic);
        Serial.print(": ");
        Serial.println(payload, precision);
    #endif
    
    mqttClient.print(payload, precision);

    if (!mqttClient.endMessage())
        DEBUG_PRINT("MQTT end message failed");
}


inline void mqttPublish(const char *topic, const char *payload) {
    if (!mqttClient.beginMessage(topic, false, 1, false)) {
        DEBUG_PRINT("MQTT begin message failed");
        return;
    }

    #ifdef DEBUG
        Serial.print(topic);
        Serial.print(": ");
        Serial.println(payload);
    #endif
    mqttClient.print(payload);

    if (!mqttClient.endMessage())
        DEBUG_PRINT("MQTT end message failed");
}


void wifiConnect() {
    DEBUG_PRINT("Connecting to WiFi");
    while (WiFi.begin(SSID, PASS) != WL_CONNECTED) {
        DEBUG_PRINT("Retrying...");
        delay(5000);
        WiFi.disconnect();
    }
    DEBUG_PRINT("Connected!");
}
