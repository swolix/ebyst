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
from ..device import Pin

class I2C:
    class NackError(Exception):
        def __init__(self):
            Exception.__init__(self, "I2C Nack")

    def __init__(self, ctl, SCL: Pin, SDA: Pin, address_bits=8, data_bits=8):
        self.ctl = ctl
        self.SCL = SCL
        self.SDA = SDA
        self.address_bits = address_bits
        self.data_bits = data_bits

    async def init(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SCL.set_value(1)
        self.SDA.set_value(1)
        await self.ctl.cycle()

    async def _start(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SDA.set_value(0)
        await self.ctl.cycle(sample=False)
        self.SCL.set_value(0)
        await self.ctl.cycle(sample=False)
    
    async def _clock_out_bit(self, bit: int):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SDA.set_value(bit)
        await self.ctl.cycle(sample=False)
        self.SCL.set_value(1)
        await self.ctl.cycle(sample=False)
        self.SCL.set_value(0)
        await self.ctl.cycle(sample=False)

    async def _clock_in_bit(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(False)
        await self.ctl.cycle(sample=False)
        self.SCL.set_value(1)
        await self.ctl.cycle()
        r = self.SDA.get_value()
        self.SCL.set_value(0)
        await self.ctl.cycle(sample=False)
        return r

    async def _restart(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SDA.set_value(1)
        await self.ctl.cycle(sample=False)
        self.SCL.set_value(1)
        await self.ctl.cycle(sample=False)
        self.SDA.set_value(0)
        await self.ctl.cycle(sample=False)
        self.SCL.set_value(0)
        await self.ctl.cycle(sample=False)

    async def _stop(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SCL.set_value(1)
        await self.ctl.cycle(sample=False)
        self.SDA.set_value(1)
        await self.ctl.cycle(sample=False)

    async def write(self, dev_address, reg_address, data):
        await self._start()

        for i in range(7):
            await self._clock_out_bit((dev_address >> (7-i)) & 1)
        await self._clock_out_bit(0)
        if await self._clock_in_bit(): raise I2C.NackError()

        for i in range(self.address_bits):
            await self._clock_out_bit((reg_address >> (self.address_bits-1-i)) & 1)
        if await self._clock_in_bit(): raise I2C.NackError()

        for i in range(8):
            await self._clock_out_bit((data >> (7-i)) & 1)
        if await self._clock_in_bit(): raise I2C.NackError()

        await self._stop()

    async def read(self, dev_address, reg_address):
        d = 0
        await self._start()

        for i in range(7):
            await self._clock_out_bit((dev_address >> (7-i)) & 1)
        await self._clock_out_bit(0)
        await self._clock_in_bit()

        for i in range(self.address_bits):
            await self._clock_out_bit((reg_address >> (self.address_bits-1-i)) & 1)
        await self._clock_in_bit()

        await self._restart()

        for i in range(7):
            await self._clock_out_bit((dev_address >> (7-i)) & 1)
        await self._clock_out_bit(1)
        await self._clock_in_bit()

        for i in range(8):
            d <<= 1 
            d |= await self._clock_in_bit()
        await self._clock_in_bit()

        await self._stop()

        return d