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

    def init(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SCL.set_value(1)
        self.SDA.set_value(1)
        self.ctl.cycle()

    def _start(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SDA.set_value(0)
        self.ctl.cycle()
        self.SCL.set_value(0)
        self.ctl.cycle()
    
    def _clock_out_bit(self, bit: int):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SDA.set_value(bit)
        self.ctl.cycle()
        self.SCL.set_value(1)
        self.ctl.cycle()
        self.SCL.set_value(0)
        self.ctl.cycle()

    def _clock_in_bit(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(False)
        self.ctl.cycle()
        self.SCL.set_value(1)
        self.ctl.cycle()
        r = self.SDA.get_value()
        self.SCL.set_value(0)
        self.ctl.cycle()
        return r

    def _restart(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SDA.set_value(1)
        self.ctl.cycle()
        self.SCL.set_value(1)
        self.ctl.cycle()
        self.SDA.set_value(0)
        self.ctl.cycle()
        self.SCL.set_value(0)
        self.ctl.cycle()


    def _stop(self):
        self.SCL.output_enable(True)
        self.SDA.output_enable(True)
        self.SCL.set_value(1)
        self.ctl.cycle()
        self.SDA.set_value(1)
        self.ctl.cycle()

    def write(self, dev_address, reg_address, data):
        self._start()

        for i in range(7):
            self._clock_out_bit((dev_address >> (7-i)) & 1)
        self._clock_out_bit(0)
        if self._clock_in_bit(): raise I2C.NackError()

        for i in range(self.address_bits):
            self._clock_out_bit((reg_address >> (self.address_bits-1-i)) & 1)
        if self._clock_in_bit(): raise I2C.NackError()

        for i in range(8):
            self._clock_out_bit((data >> (7-i)) & 1)
        if self._clock_in_bit(): raise I2C.NackError()

        self._stop()

    def read(self, dev_address, reg_address):
        d = 0
        self._start()

        for i in range(7):
            self._clock_out_bit((dev_address >> (7-i)) & 1)
        self._clock_out_bit(0)
        self._clock_in_bit()

        for i in range(self.address_bits):
            self._clock_out_bit((reg_address >> (self.address_bits-1-i)) & 1)
        self._clock_in_bit()

        self._restart()

        for i in range(7):
            self._clock_out_bit((dev_address >> (7-i)) & 1)
        self._clock_out_bit(1)
        self._clock_in_bit()

        for i in range(8):
            d <<= 1 
            d |= self._clock_in_bit()
        self._clock_in_bit()

        self._stop()

        return d