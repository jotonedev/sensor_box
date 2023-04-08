# Sensor box v1

<img alt="Final result" src="img/final_01.avif"  width="600">

## Objective

Create a system capable of collecting environmental data and sending it to an MQTT broker by connecting to WiFi.

## Data to collect

- temperature (AHT20)
- humidity (AHT20)
- air quality (PMS7003, SGP30)
- atmospheric pressure (BMP180)

## Power supply

- 3.3V lithium battery
- solar panel

## Operation

Every 60 seconds, the system wakes up from a sleep state, checks the WiFi connection, collects and sends data to the
MQTT broker. During the interval of time between one transmission and the next, the system goes into a sleep state to
consume as little energy as possible.

## Topics MQTT

- `box01/temperature` (float, °C)
- `box01/humidity` (int, %)
- `box01/pressure` (int, Pa)
- `box01/caqi` (int)
- `box01/pm01` (int, ug/m3)
- `box01/pm25` (int, ug/m3)
- `box01/pm100` (int, ug/m3)
- `box01/eco2` (int, ppm)
- `box01/tvoc` (int, ppb)
- `box01/h2` (int, ppm)
- `box01/ethanol` (int, ppm)

## Circuit Diagram

<img alt="Breadboard view" src="img/breadboard.png"  width="600">

## Hardware used

- Raspberry Pi Pico W (RP2040) or ESP32
- AHT20
- BMP180
- PMS7003
- SGP30
- Step-up converter 3.3 V - 5 V
- Solar panel
- CN3065
- 3.3V lithium battery

## License

[MIT License](LICENSE.md)

## Authors

- [John Toniutti](https://jotone.eu)

## Notes

- Currently, the DORMANT state isn't used because it doesn't work correctly.
