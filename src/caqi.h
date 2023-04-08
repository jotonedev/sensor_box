#ifndef CAQI_H
#define CAQI_H

#include <Arduino.h>

int calculate_caqi(uint16_t pm25, uint16_t pm10);

inline int calculate_caqi_pm10(uint16_t pm10);

inline int calculate_caqi_pm25(uint16_t pm25);


int calculate_caqi(uint16_t pm25, uint16_t pm10) {
    int aqi_pm25 = calculate_caqi_pm25(pm25);
    int aqi_pm10 = calculate_caqi_pm10(pm10);
    return max(aqi_pm25, aqi_pm10);
}

inline int calculate_caqi_pm10(uint16_t pm10) {
    if (pm10 <= 15) {
        return map(pm10, 0, 25, 0, 25);
    } else if (pm10 <= 30) {
        return map(pm10, 26, 50, 26, 50);
    } else if (pm10 <= 55) {
        return map(pm10, 51, 90, 51, 75);
    } else if (pm10 <= 110) {
        return map(pm10, 91, 180, 76, 100);
    } else {
        return 100;
    }
}

inline int calculate_caqi_pm25(uint16_t pm25) {
    if (pm25 <= 15) {
        return map(pm25, 0, 15, 0, 25);
    } else if (pm25 <= 30) {
        return map(pm25, 16, 30, 26, 50);
    } else if (pm25 <= 55) {
        return map(pm25, 31, 55, 51, 75);
    } else if (pm25 <= 110) {
        return map(pm25, 56, 110, 76, 100);
    } else {
        return 100;
    }
}

#endif