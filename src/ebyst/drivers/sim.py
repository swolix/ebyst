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
import logging

from bitarray import bitarray

from .driver import Driver
from ..tap_controller import State
from ..device import Device

logger = logging.getLogger(__name__)

class Sim(Driver):
    def __init__(self, device: Device):
        Driver.__init__(self)
        self.device = device
        self.reset()

    def reset(self):
        self.state = State.TEST_LOGIC_RESET
        self.shift_ir = 0
        self.ir = 1
        self.dr_size = 1
        self.shift_dr = 0

    def transfer(self, tms, tdi):
        assert tms in (0, 1)
        assert tdi in (0, 1)

        tdo = 0
        next_state = self.state
        if self.state == State.TEST_LOGIC_RESET:
            if tms == 0:
                next_state = State.RUN_TEST_IDLE
        elif self.state == State.RUN_TEST_IDLE:
            if tms == 1:
                next_state = State.SELECT_DR_SCAN
        elif self.state == State.SELECT_DR_SCAN:
            if tms == 0:
                next_state = State.CAPTURE_DR
            elif tms == 1:
                next_state = State.SELECT_IR_SCAN
        elif self.state == State.CAPTURE_DR:
            if self.ir == self.device.opcodes['IDCODE']:
                logger.info("Shifting out ID code")
                self.shift_dr = self.device.idcode.to_bitarray()
                self.dr_size = 32
            elif self.ir == self.device.opcodes['BYPASS']:
                logger.info("Bypass")
                self.shift_dr = bitarray('0')
                self.dr_size = 1
            elif self.ir == self.device.opcodes['SAMPLE']:
                logger.info("Sample")
                self.shift_dr = bitarray('0')
                self.dr_size = len(self.device.cells)
            elif self.ir == self.device.opcodes['EXTEST']:
                logger.info("Extest")
                self.shift_dr = bitarray('0')
                self.dr_size = len(self.device.cells)
            else:
                logger.warning(f"Unknown IR bin({self.ir})")
                self.shift_dr = bitarray('0')
                self.dr_size = 1

            if tms == 0:
                next_state = State.SHIFT_DR
            elif tms == 1:
                next_state = State.EXIT1_DR
        elif self.state == State.SHIFT_DR:
            tdo = self.shift_dr[0]
            self.shift_dr = self.shift_dr[1:]
            self.shift_dr.append(tdi)
            if tms == 1:
                next_state = State.EXIT1_DR
        elif self.state == State.EXIT1_DR:
            if tms == 0:
                next_state = State.PAUSE_DR
            elif tms == 1:
                next_state = State.UPDATE_DR
        elif self.state == State.PAUSE_DR:
            if tms == 1:
                next_state = State.EXIT2_DR
        elif self.state == State.EXIT2_DR:
            if tms == 0:
                next_state = State.SHIFT_DR
            elif tms == 1:
                next_state = State.UPDATE_DR
        elif self.state == State.UPDATE_DR:
            if tms == 0:
                next_state = State.RUN_TEST_IDLE
            elif tms == 1:
                next_state = State.SELECT_DR_SCAN
        elif self.state == State.SELECT_IR_SCAN:
            if tms == 0:
                next_state = State.CAPTURE_IR
            elif tms == 1:
                next_state = State.TEST_LOGIC_RESET
        elif self.state == State.CAPTURE_IR:
            self.ir = bitarray('0' * self.device.irlen) # TODO take INSTRUCTION_CAPTURE from BSDL
            self.shift_ir = self.ir
            if tms == 0:
                next_state = State.SHIFT_IR
            elif tms == 1:
                next_state = State.EXIT1_IR
        elif self.state == State.SHIFT_IR:
            tdo = self.shift_ir[0]
            self.shift_ir = self.shift_ir[1:]
            self.shift_ir.append(tdi)
            if tms == 1:
                next_state = State.EXIT1_IR
        elif self.state == State.EXIT1_IR:
            if tms == 0:
                next_state = State.PAUSE_IR
            elif tms == 1:
                next_state = State.UPDATE_IR
        elif self.state == State.PAUSE_IR:
            if tms == 1:
                next_state = State.EXIT2_IR
        elif self.state == State.EXIT2_IR:
            if tms == 0:
                next_state = State.SHIFT_IR
            elif tms == 1:
                next_state = State.UPDATE_IR
        elif self.state == State.UPDATE_IR:
            self.ir = self.shift_ir
            logger.info(f"Current instruction: {self.ir}")
            if tms == 0:
                next_state = State.RUN_TEST_IDLE
            elif tms == 1:
                next_state = State.SELECT_DR_SCAN
        else:
            assert False

        if self.state != next_state:
            logger.debug(f"State {self.state.name} => {next_state.name}")
            self.state = next_state

        return tdo

class SimChain(Driver):
    def __init__(self, devices: list[Sim] = []):
        self.devices = devices

    def transfer(self, tms, tdi):
        for device in self.devices:
            tdi = device.transfer(tms, tdi)
        return tdi