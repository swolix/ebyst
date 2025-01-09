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
    def __init__(self, ctl, CK: DiffPin, RESETn: Pin, CSn: Pin, RWDS: Pin, DQ: PinGroup):
        self.ctl = ctl
        self.CK = CK
        self.RESETn = RESETn
        self.CSn = CSn
        self.RWDS = RWDS
        self.DQ = DQ
        self.DQ.endian = 'little'

    async def init(self):
        self.CK.output_enable(True)
        self.RESETn.output_enable(True)
        self.CSn.output_enable(True)
        self.RWDS.output_enable(False)
        self.DQ.output_enable(False)
        self.CK.set_value(0)
        self.RESETn.set_value(0)
        self.CSn.set_value(1)
        await self.ctl.cycle()
        self.RESETn.set_value(1)
        await self.ctl.cycle()

    async def read(self, address, length=4, reg_space=False):
        try:
            self.DQ.output_enable(True)
            self.CSn.set_value(0)

            ca = [0x80 | (0x40 if reg_space else 0x00) | ((address >> 27) & 0x1f),
                (address >> 19) & 0xff,
                (address >> 11) & 0xff,
                (address >>  3) & 0xff,
                0,
                address & 0x07]

            for i in range(3):
                self.DQ.set_value(ca[2*i+0])
                await self.ctl.cycle()
                self.CK.set_value(1)
                await self.ctl.cycle()
                self.DQ.set_value(ca[2*i+1])
                await self.ctl.cycle()
                self.CK.set_value(0)
                await self.ctl.cycle()

            self.DQ.output_enable(False)

            r = []
            rwds_d = rwds_dd = 0
            for i in range((2*7+length//2)*4+50):
                self.CK.set_value(1 if i & 2 else 0)
                await self.ctl.cycle()

                if rwds_dd != rwds_d: r.append(self.DQ.get_value())
                rwds_dd = rwds_d
                rwds_d = self.RWDS.get_value()

                if len(r) == length: break

            if len(r) != length:
                raise Exception("HyperRAM not responding")
        finally:
            self.CSn.set_value(1)
            await self.ctl.cycle()
            self.DQ.output_enable(False)
            self.CK.set_value(0)
            await self.ctl.cycle()

        return r

    async def write(self, address, data, reg_space=False):
        try:
            self.DQ.output_enable(True)
            self.CSn.set_value(0)

            ca = [0x00 | (0x40 if reg_space else 0x00) | ((address >> 27) & 0x1f),
                (address >> 19) & 0xff,
                (address >> 11) & 0xff,
                (address >>  3) & 0xff,
                0,
                address & 0x07]

            for i in range(3):
                self.DQ.set_value(ca[2*i+0])
                await self.ctl.cycle()
                self.CK.set_value(1)
                await self.ctl.cycle()
                self.DQ.set_value(ca[2*i+1])
                await self.ctl.cycle()
                self.CK.set_value(0)
                await self.ctl.cycle()

            for i in range(2*7-1):
                await self.ctl.cycle()
                self.CK.set_value(1)
                await self.ctl.cycle()
                await self.ctl.cycle()
                self.CK.set_value(0)
                await self.ctl.cycle()

            self.RWDS.output_enable(True)
            self.RWDS.set_value(0)
            for i in range(len(data)//2):
                self.DQ.set_value(data[2*i])
                await self.ctl.cycle()
                self.CK.set_value(1)
                await self.ctl.cycle()
                self.DQ.set_value(data[2*i+1])
                await self.ctl.cycle()
                self.CK.set_value(0)
                await self.ctl.cycle()

        finally:
            self.CSn.set_value(1)
            await self.ctl.cycle()
            self.RWDS.output_enable(False)
            self.DQ.output_enable(False)
            await self.ctl.cycle()
