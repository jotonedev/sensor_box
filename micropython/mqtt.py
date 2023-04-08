# The MIT License (MIT)
#
# Copyright (c) 2013, 2014 micropython-lib contributors
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

import micropython

import usocket as socket
import ustruct as struct

__all__ = ["MQTTClient"]


class MQTTClient:
    def __init__(
            self,
            client_id: str,
            server: str,
            port: int = 1883,
            user: str = None,
            password: str = None,
            keepalive: int = 0
    ):
        self.client_id = client_id
        self.sock: socket.Socket = None
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive

    def _send_str(self, s: str) -> None:
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self) -> int:
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7F) << sh
            if not b & 0x80:
                return n
            sh += 7

    @micropython.native
    def connect(self, clean_session=True) -> int:
        self.sock = socket.socket()
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock.connect(addr)

        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\x04MQTT\x04\x02\0\0")

        sz = 10 + 2 + len(self.client_id)
        msg[6] = clean_session << 1

        if self.user is not None:
            sz += 2 + len(self.user) + 2 + len(self.password)
            msg[6] |= 0xC0

        if self.keepalive:
            msg[7] |= self.keepalive >> 8
            msg[8] |= self.keepalive & 0x00FF

        i = 1
        while sz > 0x7F:
            premsg[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        premsg[i] = sz

        # noinspection PyArgumentList
        self.sock.write(premsg, i + 2)
        self.sock.write(msg)

        self._send_str(self.client_id)
        if self.user is not None:
            self._send_str(self.user)
            self._send_str(self.password)
        resp = self.sock.read(4)

        return resp[2] & 1

    def disconnect(self) -> None:
        self.sock.write(b"\xe0\0")
        self.sock.close()

    def ping(self) -> bool:
        try:
            self.sock.write(b"\xc0\0")
        except OSError:
            return False

        return True

    @micropython.native
    def publish(self, topic: str, msg: str) -> None:
        pkt = bytearray(b"0\0\0\0")

        sz = 2 + len(topic) + len(msg)
        i = 1
        while sz > 0x7F:
            pkt[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        pkt[i] = sz

        # noinspection PyArgumentList
        self.sock.write(pkt, i + 1)
        self._send_str(topic)
        self.sock.write(msg)

    @micropython.native
    def wait_msg(self) -> int:
        """
        Wait for a single incoming MQTT message and process it.
        Subscribed messages are delivered to a callback previously
        set by .set_callback() method. Other (internal) MQTT
        messages processed internally.
        """
        res = self.sock.read(1)
        self.sock.setblocking(True)
        if res is None:
            return 0
        if res == b"":
            return 0
        if res == b"\xd0":  # PINGRESP
            return 0
        op = res[0]
        if op & 0xF0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]

        sz -= topic_len + 2

        if op & 6 == 2:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2

            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)

        return op
