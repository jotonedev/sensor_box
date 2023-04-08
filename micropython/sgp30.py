# The MIT License (MIT)
#
# Copyright (c) 2017 ladyada for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import math
from time import sleep_ms

import micropython
from machine import I2C
from micropython import const

__all__ = ["SGP30"]

_SGP30_DEFAULT_I2C_ADDR: int = const(0x58)
_SGP30_FEATURESET_0: int = const(0x0020)
_SGP30_FEATURESET_1: int = const(0x0022)

_SGP30_CRC8_POLYNOMIAL: int = const(0x31)
_SGP30_CRC8_INIT: int = const(0xFF)
_SGP30_WORD_LEN: int = const(2)


class SGP30:
    """
    A driver for the SGP30 gas sensor.

    :param i2c: The `I2C` object to use. This is the only required parameter.
    :param int address: (optional) The I2C address of the device.
    """

    def __init__(self, i2c: I2C, address: int = _SGP30_DEFAULT_I2C_ADDR):
        """Initialize the sensor, get the serial # and verify that we found a proper SGP30"""
        self._i2c = i2c
        self._addr: int = address

        # get unique serial, its 48 bits, so we store in an array
        self.serial = self._i2c_read_words_from_cmd([0x36, 0x82], 10, 3)
        # get featureset
        featureset = self._i2c_read_words_from_cmd([0x20, 0x2f], 10, 1)
        if featureset[0] not in [_SGP30_FEATURESET_0, _SGP30_FEATURESET_1]:
            raise RuntimeError('SGP30 Not detected')
        self.iaq_init()

    @property
    def tvoc(self) -> int:
        """Total Volatile Organic Compound in parts per billion."""
        return self.iaq_measure()[1]

    @property
    def baseline_tvoc(self) -> int:
        """Total Volatile Organic Compound baseline value"""
        return self.get_iaq_baseline()[1]

    @property
    def co2eq(self) -> int:
        """Carbon Dioxide Equivalent in parts per million"""
        return self.iaq_measure()[0]

    @property
    def baseline_co2eq(self) -> int:
        """Carbon Dioxide Equivalent baseline value"""
        return self.get_iaq_baseline()[0]

    def iaq_init(self) -> None:
        """Initialize the IAQ algorithm"""
        self._i2c_read_words_from_cmd([0x20, 0x03], 10, 0)

    def iaq_measure(self) -> list[int]:
        """Measure the CO2eq and TVOC"""
        # name, command, signals, delay
        return self._i2c_read_words_from_cmd([0x20, 0x08], 50, 2)

    def get_iaq_baseline(self) -> list[int]:
        """Retrieve the IAQ algorithm baseline for CO2eq and TVOC"""
        return self._i2c_read_words_from_cmd([0x20, 0x15], 10, 2)

    def set_iaq_baseline(self, co2eq: int, tvoc: int) -> None:
        """Set the previously recorded IAQ algorithm baseline for CO2eq and TVOC"""
        if co2eq == 0 and tvoc == 0:
            raise RuntimeError('Invalid baseline')
        buffer = []
        for value in [tvoc, co2eq]:
            # noinspection PyListCreation
            arr = [value >> 8, value & 0xFF]
            arr.append(self._generate_crc(arr))
            buffer += arr

        self._i2c_read_words_from_cmd([0x20, 0x1e] + buffer, 10, 0)

    @micropython.native
    def set_iaq_rel_humidity(self, rh: float, temp: float) -> None:
        """Set the relative humidity in % for eCO2 and TVOC compensation algorithm"""
        # Formula from "Generic SGP Driver Integration for Software I2C"
        grams_pm3 = rh / 100.0 * 6.112 * math.exp(17.62 * temp / (243.12 + temp))
        grams_pm3 *= 216.7 / (273.15 + temp)

        self.set_iaq_humidity(grams_pm3)

    def set_iaq_humidity(self, grams_pm3: float) -> None:
        """Set the humidity in g/m3 for eCO2 and TVOC compensation algorithm"""
        tmp = int(grams_pm3 * 256)
        buffer = []
        for value in [tmp]:
            # noinspection PyListCreation
            arr = [value >> 8, value & 0xFF]
            arr.append(self._generate_crc(arr))
            buffer += arr

        self._i2c_read_words_from_cmd([0x20, 0x61] + buffer, 10, 0)

    @micropython.native
    def _i2c_read_words_from_cmd(self, command: list[int], delay: int, reply_size: int) -> list[int]:
        """Run an SGP command query, get a reply and CRC results if necessary"""
        self._i2c.writeto(self._addr, bytes(command))
        sleep_ms(delay)
        if not reply_size:
            return []
        crc_result = bytearray(reply_size * (_SGP30_WORD_LEN + 1))
        self._i2c.readfrom_into(self._addr, crc_result)
        # print("\tRaw Read: ", crc_result)
        result = []
        for i in range(reply_size):
            word = [crc_result[3 * i], crc_result[3 * i + 1]]
            crc = crc_result[3 * i + 2]
            if self._generate_crc(word) != crc:
                raise RuntimeError("CRC Error")
            result.append(word[0] << 8 | word[1])
        # print("\tOK Data: ", [hex(i) for i in result])
        return result

    @staticmethod
    @micropython.native
    def _generate_crc(data) -> int:
        """8-bit CRC algorithm for checking data"""
        crc = _SGP30_CRC8_INIT
        # calculates 8-Bit checksum with given polynomial
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ _SGP30_CRC8_POLYNOMIAL
                else:
                    crc <<= 1
        return crc & 0xFF
