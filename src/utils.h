#ifndef UTILS_H
#define UTILS_H

#include <Arduino.h>


struct TempData {
    float temperature = 0.0f;
    float humidity = 0.0f;
} typedef TempData;


#ifdef ARDUINO_ARCH_RP2040
#include <pico/stdlib.h>
#include <hardware/vreg.h>

inline void lightsleep(unsigned long seconds) {
    set_sys_clock_khz(10000, false);
    vreg_set_voltage(VREG_VOLTAGE_0_95);

    delay(1000 * seconds);
    
    vreg_set_voltage(VREG_VOLTAGE_DEFAULT);
    set_sys_clock_khz(64000, false);
    delay(50);
}

#elif ARDUINO_ARCH_ESP32

inline void lightsleep(unsigned long seconds) {
    esp_sleep_enable_timer_wakeup(1000000 * seconds); //10 seconds
    esp_light_sleep_start();
}

#else

inline void lightsleep(unsigned long seconds) {
    delay(1000 * seconds);
}

#endif

uint32_t getAbsoluteHumidity(float temperature, float humidity) {
    // approximation formula from Sensirion SGP30 Driver Integration chapter 3.15
    const float absoluteHumidity = 216.7f * ((humidity / 100.0f) * 6.112f *
                                             exp((17.62f * temperature) / (243.12f + temperature)) /
                                             (273.15f + temperature)); // [g/m^3]
    const uint32_t absoluteHumidityScaled = static_cast<uint32_t>(1000.0f * absoluteHumidity); // [mg/m^3]
    
    return absoluteHumidityScaled;
}

#endif