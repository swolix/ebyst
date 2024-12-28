# Copyright (c) 2024 Sijmen Woutersen
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
import time
from bitarray import bitarray
from bitarray.util import ba2int, int2ba

import pyftdi
from pyftdi.ftdi import Ftdi

from .driver import Driver

class MPSSE(Driver):
    def __init__(self, url):
        Driver.__init__(self)

        self.url = url
        self.ftdi = Ftdi()
        self.ftdi.open_mpsse_from_url(self.url, direction=1|2|8, initial=0, frequency=1e6, latency=1)
        self.ftdi.reset()

    def set_freq(self, freq):
        freq_orig = freq
        while self.ftdi.set_frequency(freq) > freq_orig:
            freq *= 0.9

    def _read_bytes(self, count):
        r = bytearray()
        while len(r) < count:
            r += self.ftdi.read_data(count - len(r))
        return r

    @staticmethod
    def list_devices(custom_product_ids=[]):
        for custom_product_id in custom_product_ids:
            Ftdi.add_custom_vendor(custom_product_id[0])
            Ftdi.add_custom_product(custom_product_id[0], custom_product_id[1])

        urls = []
        for dev, ifaces in Ftdi.list_devices():
            urls.append(f"ftdi://0x{dev.vid:04x}:0x{dev.pid:04x}:{dev.sn}/1")
        return urls

    def transfer(self, tms, tdi):
        self.ftdi.write_data(bytearray((Ftdi.RW_BITS_TMS_PVE_NVE, 0, (0x80 if tdi else 0) | (1 if tms else 0))))
        rd = self._read_bytes(1)
        return (rd[0] & 0x80) >> 7

    def transmit_tms_str(self, tms_str: bitarray, tdi=0):
        tdi = 0x80 if tdi else 0
        for i in range(0, len(tms_str), 7):
            part = tms_str[i:i+7].copy()
            part.reverse()
            self.ftdi.write_data(bytearray((Ftdi.WRITE_BITS_TMS_NVE, len(part)-1, tdi | ba2int(part))))

    def transmit_tdi_str(self, tdi_str: bitarray, first_tms=0, last_tms=None):
        if last_tms is None: last_tms = first_tms
        if len(tdi_str) < 1: raise ValueError("n must be > 0")
        if len(tdi_str) == 1 and first_tms != last_tms: raise ValueError("last_tms must be first_tms when n == 1")

        tdi_str = tdi_str.copy()
        last_tdi = tdi_str.pop()
        if len(tdi_str) > 0:
            self.ftdi.write_data(bytearray((Ftdi.WRITE_BITS_TMS_NVE, 0, (tdi_str[0] << 7) | (1 if first_tms else 0))))
            for i in range(1, len(tdi_str), 8):
                part = tdi_str[i:i+8].copy()
                part.reverse()
                self.ftdi.write_data(bytearray((Ftdi.WRITE_BITS_NVE_LSB, len(part)-1, ba2int(part))))
        self.ftdi.write_data(bytearray((Ftdi.WRITE_BITS_TMS_NVE, 0, (last_tdi << 7) | (1 if last_tms else 0))))

    def transfer_tdi_tdo_str(self, tdi_str: bitarray, first_tms=0, last_tms=0) -> bitarray:
        if last_tms is None: last_tms = first_tms
        if len(tdi_str) < 1: raise ValueError("n must be > 0")
        if len(tdi_str) == 1 and first_tms != last_tms: raise ValueError("last_tms must be first_tms when n == 1")

        tdi_str = tdi_str.copy()
        last_tdi = tdi_str.pop()

        # NOTE: write all commands first, read results below for highest throughput,
        #       requires enough buffer size on FTDI/PC, not sure if this is an issue

        i = 0
        if len(tdi_str) > 0:
            self.ftdi.write_data(bytearray((Ftdi.RW_BITS_TMS_PVE_NVE, 0, (0x80 if tdi_str[0] else 0) | (1 if first_tms else 0))))
            i += 1
        for i in range(1, len(tdi_str), 8):
            part = tdi_str[i:i+8].copy()
            part.reverse()
            self.ftdi.write_data(bytearray((Ftdi.RW_BITS_PVE_NVE_LSB, len(part)-1, ba2int(part))))
        self.ftdi.write_data(bytearray((Ftdi.RW_BITS_TMS_PVE_NVE, 0, (0x80 if last_tdi else 0) | (1 if last_tms else 0))))

        r = bitarray()
        if len(tdi_str) > 0:
            r.append(self._read_bytes(1)[0] & 1)
        for i in range(1, len(tdi_str), 8):
            part = tdi_str[i:i+8]
            r += int2ba(self._read_bytes(1)[0] >> (8 - len(part)), len(part), 'little')
        r.append(self._read_bytes(1)[0] & 1)
        return r

    def receive_tdo_str(self, n, first_tms=0, first_tdi=0, last_tms=None, last_tdi=None) -> bitarray:
        r = bitarray()
        if last_tms is None: last_tms = first_tms
        if last_tdi is None: last_tdi = first_tdi
        if n < 1: raise ValueError("n must be > 0")
        if n == 1 and first_tms != last_tms: raise ValueError("last_tms must be first_tms when n == 1")
        if n == 1 and first_tdi != last_tdi: raise ValueError("last_tdi must be first_tdi when n == 1")
        if n > 1:
            r.append(self.transfer(first_tms, first_tdi))
            n = n - 1
        while n > 256+8:
            self.ftdi.write_data(bytearray((Ftdi.READ_BYTES_PVE_LSB, 31, 0)))
            for x in self._read_bytes(32):
                r += int2ba(x, 8, 'little')
            n = n - 256
        while n > 8:
            self.ftdi.write_data(bytearray((Ftdi.READ_BYTES_PVE_LSB, 0, 0)))
            for x in self._read_bytes(1):
                r += int2ba(x, 8, 'little')
            n = n - 8
        if n > 1:
            self.ftdi.write_data(bytearray((Ftdi.READ_BITS_PVE_LSB, n - 2)))
            x = self._read_bytes(1)
            r += int2ba(x[0] >> (9 - n), n - 1, 'little') # TODO; is this right?
            n = 1
        if n > 0:
            r.append(self.transfer(last_tms, last_tdi))
            n = n - 1
        return r

    def __repr__(self):
        return self.url

    @staticmethod
    def scan():
        for dev, interfaces in Ftdi.list_devices():
            for i in range(interfaces):
                yield f"ftdi://{dev.sn}/{i+1}: {dev.description}"


    def test(self):
        import random
        self.ftdi.write_data(bytearray((Ftdi.LOOPBACK_START, )))
        try:
            for i in range(100):
                tdi = random.randint(0, 1)
                tms = random.randint(0, 1)
                tdo = self.transfer(tms, tdi)
                assert tdo == tdi

            self.transmit_tms_str(bitarray("11001"), 0)
            self.transmit_tms_str(bitarray("1111111100000001"))

            self.transmit_tdi_str(bitarray("11001"))
            self.transmit_tdi_str(bitarray("1111111100000001"))

            for i in ("0", "1", "01", "10", "001", "100", "110011001", "00110011010011"):
                i = bitarray(i)
                o = self.transfer_tdi_tdo_str(bitarray(i))
                assert i == o
            for i in range(50):
                tdi = bitarray()
                for _ in range(random.randint(1, 200)):
                    tdi.append(random.randint(0, 1))
                tdo = self.transfer_tdi_tdo_str(tdi)
                assert tdi == tdo

            for tms in (0, 1):
                for first_tdi in (0, 1):
                    for last_tdi in (0, 1):
                        for n in (1, 2, 3, 4, 7, 8, 9, 10, 20, 30, 80, 1000):
                            if n == 1: last_tdi = first_tdi
                            tdo = self.receive_tdo_str(n, first_tms=tms, first_tdi=first_tdi, last_tdi=last_tdi)
                            assert len(tdo) == n
                            assert tdo[0] == first_tdi
                            assert tdo[-1] == last_tdi

        finally:
            self.ftdi.write_data(bytearray((Ftdi.LOOPBACK_END, )))
