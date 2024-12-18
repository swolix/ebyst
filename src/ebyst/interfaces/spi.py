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

from ..device import Pin

class SPI:
    def __init__(self, ctl, SCK: Pin, SSn: Pin, MOSI: Pin, MISO: Pin):
        self.ctl = ctl
        self.SCK = SCK
        self.SSn = SSn
        self.MOSI = MOSI
        self.MISO = MISO

    async def init(self):
        self.SCK.output_enable(True)
        self.SSn.output_enable(True)
        self.MOSI.output_enable(True)
        self.MISO.output_enable(False)
        self.SCK.set_value(0)
        self.SSn.set_value(1)
        await self.ctl.cycle()

    async def transfer(self, bits: bitarray):
        r = bitarray()
        self.SSn.set_value(0)

        for bit in bits:
            self.MOSI.set_value(bit)
            await self.ctl.cycle()
            self.SCK.set_value(1)
            await self.ctl.cycle()
            r.append(self.MISO.get_value())
            self.SCK.set_value(0)

        self.SSn.set_value(1)
        await self.ctl.cycle()

        return r