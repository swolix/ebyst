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
from enum import Enum, IntEnum
import logging
import asyncio

from bitarray import bitarray

from .drivers.driver import Driver
from .device import Device
from .trace import Trace

logger = logging.getLogger(__name__)

MAX_IR_CHAIN_LENGTH = 255

class State(IntEnum):
    TEST_LOGIC_RESET = 0
    RUN_TEST_IDLE = 1
    SELECT_DR_SCAN = 10
    CAPTURE_DR = 11
    SHIFT_DR = 12
    EXIT1_DR = 13
    PAUSE_DR = 14
    EXIT2_DR = 15
    UPDATE_DR = 16
    SELECT_IR_SCAN = 20
    CAPTURE_IR = 21
    SHIFT_IR = 22
    EXIT1_IR = 23
    PAUSE_IR = 24
    EXIT2_IR = 25
    UPDATE_IR = 26

class Opcode(Enum):
    BYPASS = "BYPASS"
    IDCODE = "IDCODE"
    SAMPLE = "SAMPLE"
    PRELOAD = "PRELOAD"
    EXTEST = "EXTEST"

class TapController:
    class Chain(list):
        """Chain of devices, 0 is close to TDI"""
        def __init__(self, *args, **kwargs):
            list.__init__(self, *args, **kwargs)
            self.validated = False

        @property
        def brlen(self):
            r = 0
            for dev in self:
                r += len(dev.cells)
            return r

        def generate_ir(self, instruction):
            tdi_str = bitarray()
            for dev in self:
                try:
                    tdi_str = dev.opcodes[instruction.value] + tdi_str
                except KeyError:
                    raise Exception(f"Instruction {instruction} not supported by all devices in chain")
            return tdi_str

        def generate_br(self):
            tdi_str = bitarray()
            for dev in self:
                tdi_str = dev.generate_br() + tdi_str
            return tdi_str

        def update_br(self, br):
            o = 0
            for dev in self:
                l = len(dev.cells)
                dev.update_br(br[o:o+l])
                o += l

    def __init__(self, driver: Driver, no_parallel=False):
        self.driver = driver
        self.driver.set_freq(100e3)
        self.driver.reset()
        self.state = State.TEST_LOGIC_RESET
        self.chain = TapController.Chain()
        self.in_extest = False
        self.no_parallel = no_parallel
        self.cycle_counter = 0
        self.sample = True
        self.traces = []

    def reset(self):
        self.driver.reset()
        self.state = State.TEST_LOGIC_RESET

    def load_instruction(self, instruction: Opcode):
        if not self.chain.validated: raise Exception("Chain not validated")
        tdi_str = self.chain.generate_ir(instruction)
        logger.debug(f"Loading instruction {instruction}")
        self._goto(State.SHIFT_IR)
        self.driver.transmit_tdi_str(tdi_str, first_tms=0 if len(tdi_str) > 1 else 1, last_tms=1)
        self.state = State.EXIT1_IR
        self._goto(State.UPDATE_IR)
        self.in_extest = False

    def read_register(self, n: int):
        if not self.chain.validated: raise Exception("Chain not validated")
        self._goto(State.SHIFT_DR)
        tdo = self.driver.receive_tdo_str(n, first_tms=0 if n > 1 else 1, last_tms=1)
        self.state = State.EXIT1_DR
        self._goto(State.UPDATE_DR)
        return tdo

    def write_register(self, tdi: bitarray):
        if not self.chain.validated: raise Exception("Chain not validated")
        self._goto(State.SHIFT_DR)
        self.driver.transmit_tdi_str(tdi, first_tms=0 if len(tdi) > 1 else 1, last_tms=1)
        self.state = State.EXIT1_DR
        self._goto(State.UPDATE_DR)

    def read_write_register(self, tdi: bitarray):
        if not self.chain.validated: raise Exception("Chain not validated")
        self._goto(State.SHIFT_DR)
        tdo = self.driver.transfer_tdi_tdo_str(tdi, first_tms=0 if len(tdi) > 1 else 1, last_tms=1)
        self.state = State.EXIT1_DR
        self._goto(State.UPDATE_DR)
        return tdo
    
    def detect_chain(self):
        """Detect chain length (nr of devices and total instruction register length"""
        try:
            self._goto(State.SHIFT_IR)
            # load IR with 0
            self.driver.transmit_tdi_str(bitarray('0') * MAX_IR_CHAIN_LENGTH)
            if self.driver.transfer(0, 0) != 0:
                raise Exception("Chain detection failed: 0 not coming out")
            # load IR with 1, find rising edge position
            irlen = 0
            while self.driver.transfer(0, 1) == 0:
                irlen += 1
                if irlen >= MAX_IR_CHAIN_LENGTH:
                    raise Exception("Chain detection failed: 1 not coming out")
            # IR is now all 1's => BYPASS
            self._goto(State.UPDATE_IR, 1)
            self._goto(State.SHIFT_DR)
            # load BYPASS with 0
            self.driver.transmit_tdi_str(bitarray('0') * MAX_IR_CHAIN_LENGTH)
            if self.driver.transfer(0, 0) != 0:
                raise Exception("Chain detection failed: 0 not coming out")
            # load BYPASS with 1, find rising edge position
            drlen = 0
            while self.driver.transfer(0, 1) == 0:
                drlen += 1
                if drlen >= MAX_IR_CHAIN_LENGTH:
                    raise Exception("Chain detection failed: 1 not coming out")
        finally:
            self._goto(State.TEST_LOGIC_RESET)

        logger.info(f"Found {drlen} device(s) with a total IR chain length of {irlen}")
        return (drlen, irlen)

    def add_device(self, device: Device):
        """Add device to chain"""
        self.chain.append(device)
        self.chain.validated = False

    def validate_chain(self):
        """Validate configured chain"""
        drlen, irlen = self.detect_chain()
        if len(self.chain) != 1:
            logger.warning("Multiple devices in chain are not tested")
        if drlen != len(self.chain):
            raise Exception("Incorrect nr of devices in chain ({drlen} detected)")
        if irlen != sum(dev.irlen for dev in self.chain):
            raise Exception("Incorrect total ir length ({irlen} detected)")

        max_freq = None
        for dev in self.chain:
            if max_freq is None or dev.max_freq < max_freq:
                max_freq = dev.max_freq
        if not max_freq is None:
            self.driver.set_freq(max_freq)

        try:
            self.chain.validated = True
            self.load_instruction(Opcode.IDCODE)
            idcode = self.read_register(32*drlen)
            for i, dev in enumerate(self.chain):
                if idcode[len(idcode)-i*32-32:len(idcode)-i*32] != dev.idcode:
                    raise Exception(f"IDCode doesn't match for device {i}")
            
            self.load_instruction(Opcode.SAMPLE)
            br = self.read_register(self.chain.brlen)
            self.chain.update_br(br)
        except:
            self.chain.validated = False
            raise
        finally:
            self._goto(State.RUN_TEST_IDLE)

    def extest(self):
        self.in_extest = False
        self.load_instruction(Opcode.SAMPLE)
        br = self.chain.generate_br()
        br = self.read_write_register(br)
        self.chain.update_br(br)
        self.load_instruction(Opcode.EXTEST)
        self.in_extest = True
    
    async def cycle(self, sample=True):
        """Cycle the boundary scan register when in extest() mode; updates the output pins,
            and samples the input pins

            sample: Write and read BR (if only writing; sample can be set to False providing a small speedup)
        """
        # Force a reschedule before cycling BR, this allows all tasks to share a BR cycle.
        # If we are awaken again, and no other task performed the cycle; we execute it.
        cycle_counter = self.cycle_counter
        self.sample |= sample # OR sample flags from all tasks
        if not self.no_parallel: await asyncio.sleep(0)
        if cycle_counter == self.cycle_counter:
            # nobody else performed the cycle while we where sleeping => we do it
            br = self.chain.generate_br()
            if self.sample:
                br = self.read_write_register(br)
                self.chain.update_br(br)
            else:
                self.write_register(br)
            for trace in self.traces: trace.snapshot()
            self.cycle_counter += 1
            self.sample = False

    def trace(self, fn, **pins):
        self.traces.append(Trace(fn, **pins))

    def _goto(self, target_state: State, tdi=0):
        state = self.state
        logger.debug(f"Going from {state.name} to {target_state.name}")
        tms = bitarray()
        while state != target_state:
            if state == State.TEST_LOGIC_RESET:
                tms.append(0)
                state = State.RUN_TEST_IDLE
            elif state == State.RUN_TEST_IDLE:
                tms.append(1)
                state = State.SELECT_DR_SCAN
            elif state == State.SELECT_DR_SCAN:
                if target_state > State.SELECT_DR_SCAN and target_state <= State.UPDATE_DR:
                    tms.append(0)
                    state = State.CAPTURE_DR
                else:
                    tms.append(1)
                    state = State.SELECT_IR_SCAN
            elif state == State.CAPTURE_DR:
                if target_state == State.SHIFT_DR:
                    tms.append(0)
                    state = State.SHIFT_DR
                else:
                    tms.append(1)
                    state = State.EXIT1_DR
            elif state == State.SHIFT_DR:
                tms.append(1)
                state = State.EXIT1_DR
            elif state == State.EXIT1_DR:
                if target_state in(State.PAUSE_DR, State.EXIT2_DR, State.SHIFT_DR):
                    tms.append(0)
                    state = State.PAUSE_DR
                else:
                    tms.append(1)
                    state = State.UPDATE_DR
            elif state == State.PAUSE_DR:
                tms.append(1)
                state = State.EXIT2_DR
            elif state == State.EXIT2_DR:
                if target_state in(State.SHIFT_DR, State.EXIT1_DR, State.PAUSE_DR):
                    tms.append(0)
                    state = State.SHIFT_DR
                else:
                    tms.append(1)
                    state = State.UPDATE_DR
            elif state == State.UPDATE_DR:
                if state == State.RUN_TEST_IDLE:
                    tms.append(0)
                    state = State.RUN_TEST_IDLE
                else:
                    tms.append(1)
                    state = State.SELECT_DR_SCAN
            elif state == State.SELECT_IR_SCAN:
                if target_state > State.SELECT_IR_SCAN and target_state <= State.UPDATE_IR:
                    tms.append(0)
                    state = State.CAPTURE_IR
                else:
                    tms.append(1)
                    state = State.TEST_LOGIC_RESET
            elif state == State.CAPTURE_IR:
                if target_state == State.SHIFT_IR:
                    tms.append(0)
                    state = State.SHIFT_IR
                else:
                    tms.append(1)
                    state = State.EXIT1_IR
            elif state == State.SHIFT_IR:
                tms.append(1)
                state = State.EXIT1_IR
            elif state == State.EXIT1_IR:
                if target_state in(State.PAUSE_IR, State.EXIT2_IR, State.SHIFT_IR):
                    tms.append(0)
                    state = State.PAUSE_IR
                else:
                    tms.append(1)
                    state = State.UPDATE_IR
            elif state == State.PAUSE_IR:
                tms.append(1)
                state = State.EXIT2_IR
            elif state == State.EXIT2_IR:
                if target_state in(State.SHIFT_IR, State.EXIT1_IR, State.PAUSE_IR):
                    tms.append(0)
                    state = State.SHIFT_IR
                else:
                    tms.append(1)
                    state = State.UPDATE_IR
            elif state == State.UPDATE_IR:
                if state == State.RUN_TEST_IDLE:
                    tms.append(0)
                    state = State.RUN_TEST_IDLE
                else:
                    tms.append(1)
                    state = State.SELECT_DR_SCAN
            else:
                assert False

        logger.debug(f"TMS string: {tms}")
        
        self.driver.transmit_tms_str(tms, tdi)
        self.state = state
