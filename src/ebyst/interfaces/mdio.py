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
from bitarray import bitarray
from bitarray.util import int2ba, ba2int

from ..device import Pin

class MDIO:
    def __init__(self, ctl, MDC: Pin, MDIO: Pin):
        self.ctl = ctl
        self.MDC = MDC
        self.MDIO = MDIO

    async def init(self):
        self.MDC.output_enable(True)
        self.MDIO.output_enable(True)
        self.MDC.set_value(1)
        self.MDIO.set_value(1)
        await self.ctl.cycle()

    async def send_bits(self, bits: bitarray):
        # print("S", bits)
        self.MDIO.output_enable(True)
        for bit in bits:
            self.MDC.set_value(0)
            self.MDIO.set_value(bit)
            await self.ctl.cycle()
            self.MDC.set_value(1)
            await self.ctl.cycle()

    async def recv_bits(self, n):
        r = bitarray()
        self.MDIO.output_enable(False)
        for _ in range(n):
            self.MDC.set_value(0)
            await self.ctl.cycle()
            self.MDC.set_value(1)
            await self.ctl.cycle()
            r.append(self.MDIO.get_value())
        self.MDIO.output_enable(True)
        # print("R", r)
        return r

    async def read(self, phy_address, reg_address):
        await self.send_bits(bitarray("111111111111111111111111111111110110"))
        await self.send_bits(int2ba(phy_address, length=5))
        await self.send_bits(int2ba(reg_address, length=5))
        await self.recv_bits(2)
        return ba2int(await self.recv_bits(16))
