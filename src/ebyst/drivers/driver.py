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

class Driver:
    def reset(self):
        self.transmit_tms_str(bitarray('11111'))

    def set_freq(self, freq):
        pass

    def transfer(self, tms: int, tdi: int) -> int:
        raise NotImplementedError()

    def transmit_tms_str(self, tms_str: bitarray, tdi=0):
        for tms in tms_str:
            self.transfer(tms, tdi)
    
    def transfer_tdi_tdo_str(self, tdi_str: bitarray, first_tms=0, last_tms=0) -> bitarray:
        r = bitarray()
        for tdi in tdi_str[:-1]:
            r.append(self.transfer(first_tms, tdi))
        r.append(self.transfer(last_tms, tdi_str[-1]))
        return r

    def transmit_tdi_str(self, tdi_str: bitarray, first_tms=0, last_tms=0):
        self.transfer_tdi_tdo_str(tdi_str, first_tms, last_tms)

    def receive_tdo_str(self, n, first_tms=0, first_tdi=0, last_tms=None, last_tdi=None) -> bitarray:
        if last_tms is None: last_tms = first_tms
        if last_tdi is None: last_tdi = first_tdi
        if n < 1: raise ValueError("n must be > 0")
        if n == 1 and first_tms != last_tms: raise ValueError("last_tms must be first_tms when n == 1")
        if n == 1 and first_tdi != last_tdi: raise ValueError("last_tdi must be first_tdi when n == 1")
        r = bitarray()
        for i in range(n-1):
            r.append(self.transfer(first_tms, first_tdi))
        r.append(self.transfer(last_tms, last_tdi))
        return r
