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

from ..device import Pin, DiffPin, PinGroup

class HyperRAM:
    def __init__(self, ctl, CK: DiffPin, CSn: Pin, RWDS: Pin, DQ: PinGroup):
        self.ctl = ctl
        self.CK = CK
        self.CSn = CSn
        self.RWDS = RWDS
        self.DQ = DQ

    async def init(self):
        self.CK.output_enable(True)
        self.CSn.output_enable(True)
        self.RWDS.output_enable(False)
        self.DQ.output_enable(False)
        self.CK.set_value(0)
        self.CSn.set_value(1)
        await self.ctl.cycle()

    async def read(self, address):
        self.RWDS.output_enable(True)
        self.DQ.output_enable(True)
        self.CSn.set_value(0)
        self.RWDS.set_value(1)

        ca = [0x80 | ((address >> 27) & 0x1f),
              (address >> 19) & 0xff,
              (address >> 11) & 0xff,
              (address >>  3) & 0xff,
              0,
              address & 0x07]

        for i in range(3):
            self.DQ = ca[2*i+0]
            await self.ctl.cycle()
            self.CK.set_value(1)
            await self.ctl.cycle()
            self.DQ = ca[2*i+1]
            await self.ctl.cycle()
            self.CK.set_value(0)
            await self.ctl.cycle()

        self.RWDS.output_enable(False)
        self.DQ.output_enable(False)

        for i in range(100):
            self.CK.set_value(1)
            await self.ctl.cycle()
            await self.ctl.cycle()
            self.CK.set_value(0)
            await self.ctl.cycle()
            await self.ctl.cycle()


    async def write(self, address, data):
        self.RWDS.output_enable(True)
        self.DQ.output_enable(True)
        self.CSn.set_value(0)
        self.RWDS.set_value(1)

        ca = [0x80 | ((address >> 27) & 0x1f),
              (address >> 19) & 0xff,
              (address >> 11) & 0xff,
              (address >>  3) & 0xff,
              0,
              address & 0x07]

        for i in range(3):
            self.DQ = ca[2*i+0]
            await self.ctl.cycle()
            self.CK.set_value(1)
            await self.ctl.cycle()
            self.DQ = ca[2*i+1]
            await self.ctl.cycle()
            self.CK.set_value(0)
            await self.ctl.cycle()

        for i in range(3+4):
            await self.ctl.cycle()
            self.CK.set_value(1)
            await self.ctl.cycle()
            await self.ctl.cycle()
            self.CK.set_value(0)
            await self.ctl.cycle()

        for i in range(2):
            self.DQ = (data >> (i * 8)) & 0xFF
            await self.ctl.cycle()
            self.CK.set_value(1)
            await self.ctl.cycle()
            self.DQ = (data >> ((i + 1) * 8)) & 0xFF
            await self.ctl.cycle()
            self.CK.set_value(0)
            await self.ctl.cycle()

        self.RWDS.output_enable(False)
        self.DQ.output_enable(False)
