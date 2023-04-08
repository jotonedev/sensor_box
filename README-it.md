# Sensor box

<img alt="Final result" src="img/final_01.avif"  width="600">

## Obiettivo

Creare una un sistema in grado di raccogliere dati ambientali e inviarli a un broker MQTT connettendosi al WiFi.

## Dati da raccogliere

- temperatura (AHT20)
- umidità (AHT20)
- qualità dell'aria (PMS7003, SGP30)
- pressione atmosferica (BMP180)

## Alimentazione

- batteria al litio da 3.3 V
- pannello solare

## Funzionamento

Ogni 60 secondi, il sistema si risveglia dallo stato dormiente, verifica la connessione al WiFi, raccoglie e invia i
dati al broker MQTT.
Durante l'intervallo di tempo tra un invio e l'altro, il sistema si mette in stato dormiente per consumare meno energia
possibile.

## Topic MQTT

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

## Schema elettrico

<img alt="Breadboard view" src="img/breadboard.png"  width="600">

## Hardware utilizzato

- Raspberry Pi Pico W (RP2040) or ESP32
- AHT20
- BMP180
- PMS7003
- SGP30
- Fotoresistenza
- Step-up converter 3.3 V - 5 V
- Pannello solare
- CN3065
- Batteria al litio da 3.3 V

## Licenza

[MIT License](LICENSE.md)

## Autori

- [John Toniutti](https://jotone.eu)

## Note

- Al momento, lo stato dormiente non viene usato poichè dà problemi con la scheda.
