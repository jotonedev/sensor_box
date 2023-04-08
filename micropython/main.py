import gc

import machine
import micropython
import network
import rp2
from machine import Pin, I2C, UART
from utime import time, sleep_ms, sleep

from aht20 import AHT20
from bmp180 import BMP180, BMP180_ULTRALOWPOWER
from caqi import CAQI
from conf import WIFI_COUNTRY, WIFI_SSID, WIFI_BSID, WIFI_PASS, MQTT_NAME, MQTT_HOST, MQTT_PORT
from mqtt import MQTTClient
from pms import PMS
from sgp30 import SGP30

# WiFI settings
rp2.country(WIFI_COUNTRY)

# Global variables
client = MQTTClient(MQTT_NAME, MQTT_HOST, keepalive=60, port=MQTT_PORT)
wlan: network.WLAN = None
wlan_pw = machine.Pin(23, Pin.OUT)

# I2C bus
i2c1 = I2C(1, scl=Pin(15), sda=Pin(14))

# Temperature and humidity sensor
aht20: AHT20 = AHT20(i2c1)

# Pressure sensor
bmp180: BMP180 = BMP180(i2c1, mode=BMP180_ULTRALOWPOWER)

# Air quality sensor
sgp30: SGP30 = SGP30(i2c1)
baseline_time: int = 0

# Particle sensor
uart = UART(0)
pms: PMS = PMS(uart)
pm25_sum: int = 0
pm100_sum: int = 0
pm_values: int = 0
caqi_time: int = time()


# noinspection PyBroadException
@micropython.native
def lightsleep(seconds: int):
    for _ in range(seconds * 1_000):
        machine.lightsleep(1)


def wifi_connect() -> bool:
    global wlan_pw, wlan

    if wlan_pw.value() == 0:
        wlan_pw.high()
        sleep_ms(500)

    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS, bssid=WIFI_BSID)
        print("Connecting to WiFi")

        # timeout for connection
        timeout = time() + 30
        while not wlan.isconnected():
            sleep_ms(50)
            if time() > timeout:
                print("WiFi timeout connection")
                return False

        print("Connected to Wifi")
        print("IP: " + wlan.ifconfig()[0])

    return True


def setup():
    global baseline_time

    # Reduce clock
    machine.freq(64_000_000)

    # Enable garbage collection
    gc.enable()

    # AHT20
    aht20.reset()
    if not aht20.calibrate():
        print("Could not calibrate AHT20")
        machine.deepsleep(60_000)

    # BMP180
    bmp180.initialize()

    # SGP30
    sgp30.iaq_init()
    try:
        f_co2 = open("co2eq_baseline.txt", 'r')
        f_tvoc = open("tvoc_baseline.txt", 'r')

        co2_baseline = int(f_co2.read())
        tvoc_baseline = int(f_tvoc.read())
    except (ValueError, OSError):
        print("Impossible to read SGP30 baselines!")
    else:
        print("Baselines loaded")
        sgp30.set_iaq_baseline(co2_baseline, tvoc_baseline)
        f_co2.close()
        f_tvoc.close()
    finally:
        baseline_time = time()

    # PMS7003
    pms.pas_mode()

    # Setup MQTT
    client.connect(clean_session=True)


def run():
    global baseline_time
    global pm25_sum, pm100_sum, caqi_time, pm_values

    # measure aht20 (temperature and humidity)
    aht20.read()
    temp = aht20.temperature
    hum = aht20.relative_humidity
    client.publish("box01/temperature", str(round(temp, 1)))
    client.publish("box01/humidity", str(round(hum, 0)))

    # measure bmp280 (pressure)
    pres = bmp180.pressure
    pres = int(round(pres / 10) * 10)
    client.publish("box01/pressure", str(pres))

    # measure sgp30 (co2 and tvoc)
    co2_eq, tvoc = sgp30.iaq_measure()
    client.publish("box01/eco2", str(co2_eq))
    client.publish("box01/tvoc", str(tvoc))

    if time() - baseline_time >= 3600:
        try:
            f_co2 = open("co2eq_baseline.txt", 'w')
            f_tvoc = open("tvoc_baseline.txt", 'w')

            bl_co2, bl_tvoc = sgp30.get_iaq_baseline()
            f_co2.write(str(bl_co2))
            f_tvoc.write(str(bl_tvoc))

            sgp30.set_iaq_rel_humidity(temp=temp, rh=hum)

            f_co2.close()
            f_tvoc.close()
        except OSError:
            print("Impossible to save SGP30 baselines!")
        finally:
            print("Baselines saved")
            baseline_time = time()

    # measure pms7003 (pm10, pm25, pm100)
    pms.wake_up()
    lightsleep(30)
    pms.prepare_read()
    pms_data = pms.read()
    pms.sleep()

    pm10 = pms_data[4]
    pm25 = pms_data[5]
    pm100 = pms_data[6]
    pm25_sum += pm25
    pm100_sum += pm100
    pm_values += 1

    if time() - caqi_time >= 3600:
        pm100_avg = pm100_sum // pm_values
        pm25_avg = pm25_sum // pm_values
        caqi = CAQI.caqi(pm25_avg, pm100_avg)
        client.publish("box01/caqi", str(caqi))
        pm25_sum = 0
        pm100_sum = 0
        pm_values = 0
        caqi_time = time()

    client.publish("box01/pm01", str(pm10))
    client.publish("box01/pm25", str(pm25))
    client.publish("box01/pm100", str(pm100))


try:
    print("Running setup")
    wifi_connect()
    setup()
    print("Setup complete")
except Exception as e:
    print(str(e))
    sleep_ms(50)
    machine.deepsleep(60_000)
else:
    lightsleep(30)  # wait for sensors to settle

while True:
    try:
        print("Waking up")
        wifi_connect()
        client.connect()

        print("Running main loop")
        run()

        print("Going sleep")
        client.disconnect()
        gc.collect()
    except Exception as e:
        print(str(e))
        sleep_ms(50)
        machine.deepsleep(60_000)
    else:
        sleep_ms(50)
        lightsleep(300)  # sleep for 5 minute

