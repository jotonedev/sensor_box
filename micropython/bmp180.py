# The MIT License (MIT)
# 
# Copyright (c) 2014 Sebastian Plamauer
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
# SOFTWARE

import micropython

from machine import I2C
from micropython import const
from ustruct import unpack
from utime import sleep_ms

__all__ = ["BMP180", "BMP180_ULTRALOWPOWER", "BMP180_STANDARD", "BMP180_HIGHRES", "BMP180_ULTRAHIGHRES"]

BMP180_ADDR = const(119)

BMP180_ULTRALOWPOWER = const(0)
BMP180_STANDARD = const(1)
BMP180_HIGHRES = const(2)
BMP180_ULTRAHIGHRES = const(3)

# BMP180 Registers
BMP180__AC1 = const(0xAA)
BMP180__AC2 = const(0xAC)
BMP180__AC3 = const(0xAE)
BMP180__AC4 = const(0xB0)
BMP180__AC5 = const(0xB2)
BMP180__AC6 = const(0xB4)
BMP180__B1 = const(0xB6)
BMP180__B2 = const(0xB8)
BMP180__MB = const(0xBA)
BMP180__MC = const(0xBC)
BMP180__MD = const(0xBE)

# BMP180 Instructions
BMP180_CONTROL = const(0xF4)
BMP180_TEMPDATA = const(0xF6)
BMP180_PRESSUREDATA = const(0xF6)

# Commands
BMP180_READTEMPCMD = const(0x2E)
BMP180_READPRESSURECMD = const(0x34)


class BMP180:
    """Module for the BMP180 pressure sensor."""

    def __init__(self, i2c_bus: I2C, mode: int = BMP180_STANDARD):
        # create i2c object
        self.chip_id = None
        self.i2c = i2c_bus
        self._mode = mode

        # settings to be adjusted by user
        self.oversample_setting = 3

    def initialize(self) -> None:
        # check chip id
        self.chip_id = self.i2c.readfrom_mem(BMP180_ADDR, 0xD0, 2)

        # calibrate sensor
        self._load_calibration()

    @micropython.native
    def _load_calibration(self) -> None:
        self._AC1 = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__AC1, 2))[0]
        self._AC2 = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__AC2, 2))[0]
        self._AC3 = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__AC3, 2))[0]
        self._AC4 = unpack('>H', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__AC4, 2))[0]
        self._AC5 = unpack('>H', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__AC5, 2))[0]
        self._AC6 = unpack('>H', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__AC6, 2))[0]

        self._B1 = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__B1, 2))[0]
        self._B2 = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__B2, 2))[0]
        self._MB = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__MB, 2))[0]
        self._MC = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__MC, 2))[0]
        self._MD = unpack('>h', self.i2c.readfrom_mem(BMP180_ADDR, BMP180__MD, 2))[0]

    @property
    def oversample_sett(self):
        return self.oversample_setting

    @oversample_sett.setter
    def oversample_sett(self, value):
        if value in range(4):
            self.oversample_setting = value
        else:
            self.oversample_setting = 3

    @micropython.native
    def _read_raw_temp(self) -> int:
        """Reads the raw (uncompensated) temperature from the sensor."""
        self.i2c.writeto_mem(BMP180_ADDR, BMP180_CONTROL, bytearray([BMP180_READTEMPCMD]))
        sleep_ms(5)
        UT = unpack('>H', self.i2c.readfrom_mem(BMP180_ADDR, BMP180_TEMPDATA, 2))[0]

        return UT

    @micropython.native
    def _read_raw_pressure(self) -> int:
        """Reads the raw (uncompensated) pressure level from the sensor."""
        i2c = self.i2c  # cache object to speedup things
        mode = self._mode
        i2c.writeto_mem(BMP180_ADDR, BMP180_CONTROL, bytearray([BMP180_READPRESSURECMD + (mode << 6)]))

        if mode == BMP180_ULTRALOWPOWER:
            sleep_ms(5)
        elif mode == BMP180_HIGHRES:
            sleep_ms(14)
        elif mode == BMP180_ULTRAHIGHRES:
            sleep_ms(26)
        else:
            sleep_ms(8)

        MSB = unpack('>B', i2c.readfrom_mem(BMP180_ADDR, BMP180_PRESSUREDATA, 1))[0]
        LSB = unpack('>B', i2c.readfrom_mem(BMP180_ADDR, BMP180_PRESSUREDATA + 1, 1))[0]
        XLSB = unpack('>B', i2c.readfrom_mem(BMP180_ADDR, BMP180_PRESSUREDATA + 2, 1))[0]
        UP = ((MSB << 16) + (LSB << 8) + XLSB) >> (8 - mode)

        return UP

    @property
    @micropython.viper
    def temperature(self) -> float:
        """Temperature in degree Celsius"""
        UT = self._read_raw_temp()

        # Calculate temperature
        X1 = ((UT - self._AC6) * self._AC5) >> 15
        X2 = (self._MC << 11) // (X1 + self._MD)
        B5 = X1 + X2
        temp = ((B5 + 8) >> 4) / 10.0

        return temp

    @property
    @micropython.viper
    def pressure(self) -> float:
        """Pressure in mbar"""
        UT = self._read_raw_temp()
        UP = self._read_raw_pressure()

        X1 = ((UT - self._AC6) * self._AC5) >> 15
        X2 = (self._MC << 11) // (X1 + self._MD)
        B5 = X1 + X2

        # Pressure Calculations
        B6 = B5 - 4000
        X1 = (self._B2 * (B6 * B6) >> 12) >> 11
        X2 = (self._AC2 * B6) >> 11
        X3 = X1 + X2
        B3 = (((self._AC1 * 4 + X3) << self._mode) + 2) // 4
        X1 = (self._AC3 * B6) >> 13
        X2 = (self._B1 * ((B6 * B6) >> 12)) >> 16
        X3 = ((X1 + X2) + 2) >> 2
        B4 = (self._AC4 * (X3 + 32768)) >> 15
        B7 = (UP - B3) * (50000 >> self._mode)
        if B7 < 0x80000000:
            p = (B7 * 2) // B4
        else:
            p = (B7 // B4) * 2
        X1 = (p >> 8) * (p >> 8)
        X1 = (X1 * 3038) >> 16
        X2 = (-7357 * p) >> 16
        p = p + ((X1 + X2 + 3791) >> 4)

        return p
