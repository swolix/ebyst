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