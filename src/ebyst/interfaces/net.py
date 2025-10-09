# Copyright (c) 2025 Sijmen Woutersen
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
from enum import Enum, auto

class BiasResistor(Enum):
    """Possible bias configurations for a digital line."""
    PULL_UP   = auto()   # Connect a resistor to VCC
    PULL_DOWN = auto()   # Connect a resistor to GND
    NONE      = auto()   # No bias resistor (floating)

class Net:
    """Class for testing nets between boundary scan cells

        name: net name for diagnostics
        ctls: list of controllers for all pins
        driver: driver pin (can be none for fixed pullled-up/down pins)
        receivers: receiver pin(s)
        bias: pull-up/down
    """
    def __init__(self, name: str, ctls, driver: Pin | None, receivers:Pin | list[Pin],
                 bias: BiasResistor=BiasResistor.NONE):
        self.name = name
        self.ctls = ctls
        self.driver = driver
        if isinstance(receivers, list):
            self.receivers = receivers
        else:
            self.receivers = [receivers]
        self.bias = bias

    async def test(self):
        if not self.driver is None:
            self.driver.output_enable(True)
            for receiver in self.receivers:
                receiver.output_enable(False)
            for value in (0, 1, 0, 1):
                self.driver.set_value(value)
                for i in range(2):
                    for ctl in self.ctls:
                        await ctl.cycle()
                for receiver in self.receivers:
                    if receiver.get_value() != value:
                        raise Exception(f"{self.name} - {receiver} stuck at {0 if value else 1}")

        if self.bias != BiasResistor.NONE:
            if not self.driver is None:
                self.driver.output_enable(False)
            for receiver in self.receivers:
                receiver.output_enable(False)
            for i in range(2):
                for ctl in self.ctls:
                    await ctl.cycle()
            value = 1 if self.bias == BiasResistor.PULL_UP else 0
            if not self.driver is None and self.driver.get_value() != value:
                raise Exception(f"{self.name} - {self.driver} PULL-UP/DOWN not working")
            for receiver in self.receivers:
                if receiver.get_value() != value:
                    raise Exception(f"{self.name} - {receiver} PULL-UP/DOWN not working")
