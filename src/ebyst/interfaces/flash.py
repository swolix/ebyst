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
from .spi import SPI

class MT25QU01GBBB:
    def __init__(self, ctl, C: Pin, Sn: Pin, WPn: Pin, DQ0: Pin, DQ1: Pin, RESETn: Pin, HOLDn: Pin):
        self.ctl = ctl
        self.WPn = WPn
        self.RESETn = RESETn
        self.HOLDn = HOLDn
        self.spi = SPI(ctl, SCK=C, SSn=Sn, MOSI=DQ0, MISO=DQ1)

    async def init(self):
        self.WPn.output_enable(True)
        self.RESETn.output_enable(True)
        self.HOLDn.output_enable(True)
        self.WPn.set_value(1)
        self.RESETn.set_value(0)
        self.HOLDn.set_value(1)
        await self.ctl.cycle()
        await self.spi.init()
        await self.ctl.cycle()
        self.RESETn.set_value(1)
        await self.ctl.cycle()

    async def read_id(self):
        cmd = bitarray("10011110" + 20 * "00000000")
        data = await self.spi.transfer(cmd)
        return data[8:].tobytes()
