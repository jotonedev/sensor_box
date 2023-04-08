# The MIT License (MIT)
#
# Copyright (c) 2020 Kattni Rembor for Adafruit Industries
# Copyright (c) 2020 Andreas Bühl
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from time import sleep_ms

from machine import I2C
from micropython import const

__all__ = ["AHT20"]

AHTX0_I2CADDR_DEFAULT: int = const(0x38)  # Default I2C address
AHTX0_CMD_CALIBRATE: int = const(0xE1)  # Calibration command
AHTX0_CMD_TRIGGER: int = const(0xAC)  # Trigger reading command
AHTX0_CMD_SOFTRESET: int = const(0xBA)  # Soft reset command
AHTX0_STATUS_BUSY: int = const(0x80)  # Status bit for busy
AHTX0_STATUS_CALIBRATED: int = const(0x08)  # Status bit for calibrated


class AHT20:
    def __init__(self, i2c: I2C, address: int = AHTX0_I2CADDR_DEFAULT) -> None:
        sleep_ms(20)  # 20ms delay to wake up
        self.i2c_device: I2C = i2c
        self.address: int = address

        self._buf: bytearray = bytearray(6)

        self._temp: float = -1.0
        self._humidity: float = -1.0

    def reset(self) -> None:
        """Perform a soft-reset of the AHT"""
        buf = memoryview(self._buf)
        buf[0] = AHTX0_CMD_SOFTRESET
        self.i2c_device.writeto(AHTX0_I2CADDR_DEFAULT, buf[0:1])
        sleep_ms(20)  # 20ms delay to wake up

    def calibrate(self) -> bool:
        """Ask the sensor to self-calibrate. Returns True on success, False otherwise"""
        buf = memoryview(self._buf)
        buf[0] = AHTX0_CMD_CALIBRATE
        buf[1] = 0x08
        buf[2] = 0x00
        self.i2c_device.writeto(AHTX0_I2CADDR_DEFAULT, buf[0:3])
        while self.status & AHTX0_STATUS_BUSY:
            sleep_ms(10)
        if not self.status & AHTX0_STATUS_CALIBRATED:
            return False

        return True

    @property
    def status(self) -> int:
        """The status byte initially returned from the sensor, see datasheet for details"""
        buf = memoryview(self._buf)
        self.i2c_device.readfrom_into(AHTX0_I2CADDR_DEFAULT, buf[0:1])
        # print("status: "+hex(self._buf[0]))
        return self._buf[0]

    @property
    def relative_humidity(self) -> float:
        """The measured relative humidity in percent."""
        return self._humidity

    @property
    def temperature(self) -> float:
        """The measured temperature in degrees Celsius."""
        return self._temp

    def read(self) -> None:
        """Internal function for triggering the AHT to read temp/humidity"""
        buf = memoryview(self._buf)
        buf[0] = AHTX0_CMD_TRIGGER
        buf[1] = 0x33
        buf[2] = 0x00
        self.i2c_device.writeto(AHTX0_I2CADDR_DEFAULT, buf[0:3])
        while self.status & AHTX0_STATUS_BUSY:
            sleep_ms(10)
        self.i2c_device.readfrom_into(AHTX0_I2CADDR_DEFAULT, buf[0:6])

        self._humidity = (
                (buf[1] << 12) | (buf[2] << 4) | (buf[3] >> 4)
        )
        self._humidity = (self._humidity * 100) / 0x100000
        self._temp = ((buf[3] & 0xF) << 16) | (buf[4] << 8) | buf[5]
        self._temp = ((self._temp * 200.0) / 0x100000) - 50

