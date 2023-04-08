# MIT License
#
# Copyright (c) 2018 Paweł Kucmus
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

from struct import unpack

import micropython
from time import time, sleep_ms
from machine import UART
from micropython import const

__all__ = ["PMS"]

# Commands
ACTIVE_MODE = bytearray((0x42, 0x4D, 0xE1, 0x00, 0x01, 0x01, 0x71))
PASSIVE_MODE = bytearray((0x42, 0x4D, 0xE1, 0x00, 0x00, 0x01, 0x70))
WAKE_UP = bytearray((0x42, 0x4D, 0xE4, 0x00, 0x01, 0x01, 0x74))
SLEEP = bytearray((0x42, 0x4D, 0xE4, 0x00, 0x00, 0x01, 0x73))
REQUEST_READ = bytearray((0x42, 0x4D, 0xE2, 0x00, 0x00, 0x01, 0x71))

# Message constant
START_BYTE_1 = const(0x42)
START_BYTE_2 = const(0x4d)

# Indexes
# noinspection DuplicatedCode
PMS_FRAME_LENGTH = const(0)
PMS_PM1_0 = const(1)
PMS_PM2_5 = const(2)
PMS_PM10_0 = const(3)
PMS_PM1_0_ATM = const(4)
PMS_PM2_5_ATM = const(5)
PMS_PM10_0_ATM = const(6)
PMS_PCNT_0_3 = const(7)
PMS_PCNT_0_5 = const(8)
PMS_PCNT_1_0 = const(9)
PMS_PCNT_2_5 = const(10)
PMS_PCNT_5_0 = const(11)
PMS_PCNT_10_0 = const(12)
PMS_VERSION = const(13)
PMS_ERROR = const(14)
PMS_CHECKSUM = const(15)


class PMS:
    def __init__(self, uart: UART):
        self.uart: UART = uart
        self.uart.init(9600, timeout=250, timeout_char=100)

    def act_mode(self) -> None:
        self.uart.write(ACTIVE_MODE)
        self.uart.flush()
        sleep_ms(50)

    def pas_mode(self) -> None:
        self.uart.write(PASSIVE_MODE)
        self.uart.flush()
        sleep_ms(50)

    def wake_up(self) -> None:
        self.uart.write(WAKE_UP)
        self.uart.flush()
        sleep_ms(50)

    def sleep(self) -> None:
        self.uart.write(SLEEP)
        self.uart.flush()
        sleep_ms(50)

    def prepare_read(self) -> None:
        self.uart.write(REQUEST_READ)
        self.uart.flush()
        sleep_ms(50)

    @micropython.native
    def read(self) -> tuple[int, ...]:
        uart = self.uart  # cache object to speedup things
        start_time = time()

        while time() - start_time < 5:
            if uart.any() < 1:
                continue

            if uart.read(1) != b"\x42":
                continue

            if uart.read(1) != b"\x4d":
                continue

            # we are reading 30 bytes left
            read_bytes = uart.read(30)
            if len(read_bytes) < 30:
                continue

            data = unpack('>HHHHHHHHHHHHHBBH', read_bytes)

            checksum = START_BYTE_1 + START_BYTE_2
            checksum += sum(read_bytes[:28])

            if checksum != data[PMS_CHECKSUM]:
                continue

            return data
        else:
            print("Timeout while reading data from PMS sensor")
