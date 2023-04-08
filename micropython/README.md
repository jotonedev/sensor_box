# Micropython version (prototype)

## Description

This was supposed to be the final version, but while testing I noticed that it consumed too much power and I was not able use lightsleep and deepsleep. 
So I redeveloped the project using the Arduino Framework.

## Programming language used

- [MicroPython](https://docs.micropython.org/en/latest/)

## Libraries used

- [SGP30](https://github.com/alexmrqt/micropython-sgp30)
- [PMS7003](https://github.com/pkucmus/micropython-pms7003)
- [MQTT](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py)
- [BMP180](https://github.com/micropython-IMU/micropython-bmp180)
- [AHT20](https://github.com/targetblank/micropython_ahtx0)

## Notes

- Before using the code, you must change the Wi-Fi credentials and the MQTT broker address in the `conf.py` file.
- The code is not optimized for power consumption because _currently_ the lightsleep and deepsleep are broken in the
  MicroPython firmware for the Raspberry Pi Pico W. When the firmware is fixed, the code will be updated.
