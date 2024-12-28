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
import re
from pprint import pprint

from bitarray import bitarray

from .bsdl import BSDLFile

SPACE = "[ \r\n\t]*"

RE_OPCODE = re.compile(f"{SPACE}(?P<instruction>[A-Za-z][A-Za-z_0-9]*){SPACE}\\((?P<opcode>[01]+(,{SPACE}[01]+)*)\\){SPACE}(,)?")
RE_CELL = re.compile(f"{SPACE}(?P<index>[0-9]+){SPACE}\\((?P<config>([^\\)\\(]*(\\([^\\)]*\\))*)*)\\)({SPACE},)?")

logger = logging.getLogger(__name__)

class StdLogicPattern:
    """Bit pattern supporting std_logic values"""
    def __init__(self, pattern):
        for c in pattern.upper():
            if not c in "01X": raise Exception(f"{c} not supported in bit pattern")
        self.pattern = pattern.upper()

    def __eq__(self, other):
        if len(self.pattern) != len(other): return False
        for c1, c2 in zip(self.pattern, other):
            if c1 != "X" and int(c1) != int(c2): return False
        return True

    def __str__(self):
        return f"StdLogicPattern('{self.pattern}')"

    def to_bitarray(self):
        return bitarray(self.pattern.replace("X", "0"))

class Cell:
    """Represents a boundary scan cell"""
    def __init__(self, num, cell, port, function, safe, ctl_cell=None, out_dis_ctl=None, out_dis_val=None):
        self.num = num
        self.cell = cell
        self.port = port
        self.function = function
        self.safe = safe
        self.ctl_cell = int(ctl_cell) if not ctl_cell is None else None
        self.out_dis_ctl = int(out_dis_ctl) if not out_dis_ctl is None else None
        self.out_dis_val = out_dis_val
        self.in_value = None
        self.out_value = 0

        self.set_safe()

    def set_safe(self):
        if self.safe.upper() != 'X':
            self.out_value = int(self.safe)

    def __repr__(self):
        return f"{self.cell} @ {self.num}"

    @classmethod
    def parse(cls, num, parameters):
        return cls(num, *[p.strip() for p in parameters.split(",")])

class Pin:
    """Represents a device pin"""
    def __init__(self, name):
        self.name = name
        self.input_cell = None
        self.output_cell = None
        self.control_cell = None

    def output_enabled(self):
        if self.output_cell is None:
            return False
        elif self.control_cell is None:
            if self.input_cell is None:
                return True
            else:
                raise Exception(f"Pin {self.name} has no control cell")
        else:
            return self.control_cell.out_value != self.output_cell.out_dis_ctl
    
    def output_enable(self, enable=True):
        if self.output_cell is None:
            raise Exception(f"Pin {self.name} has no output cell")
        elif self.control_cell is None:
            if not self.input_cell is None:
                raise Exception(f"Pin {self.name} has no control cell")
        else:
            if enable:
                self.control_cell.out_value = [1, 0][self.output_cell.out_dis_ctl]
            else:
                self.control_cell.out_value = self.output_cell.out_dis_ctl

    def set_value(self, value):
        if self.output_cell is None:
            raise Exception(f"Pin {self.name} has no output cell")
        self.output_cell.out_value = 1 if value else 0

    def get_value(self):
        if self.input_cell is None:
            raise Exception(f"Pin {self.name} has no input cell")
        return self.input_cell.in_value

    def __repr__(self):
        if self.output_enabled():
            return f"<PIN {self.name}: output: {self.output_cell.out_value}>"
        else:
            return f"<PIN {self.name}: input>: {self.input_cell.in_value}>"

class DiffPin(tuple):
    """Differential pin pair"""
    def __new__(cls, p: Pin, n: Pin):
        return tuple.__new__(cls, (p, n))

    @property
    def name(self):
        return self[0].name

    def output_enable(self, enable=True):
        self[0].output_enable(enable)
        self[1].output_enable(enable)

    def output_enabled(self):
        return self[0].output_enabled()

    def set_value(self, value):
        self[0].set_value(1 if value else 0)
        self[1].set_value(0 if value else 1)

    def get_value(self):
        return self[0].get_value()

    def __repr__(self):
        if self.output_enabled():
            return f"<DIFFPIN {self.name}: output: {self.get_value()}>"
        else:
            return f"<DIFFPIN {self.name}: input>: {self.get_value()}>"

class PinGroup(list):
    """Group of pins to be read/written all at once"""
    def __init__(self, initial):
        list.__init__(self, initial)

    @property
    def name(self):
        return self[0].name

    def output_enable(self, enable=True):
        for pin in self:
            pin.output_enable(enable)

    def output_enabled(self):
        return self[0].output_enabled()

    def set_value(self, value):
        for (i, pin) in enumerate(self):
            try:
                pin.set_value(value[i])
            except TypeError:
                pin.set_value((value >> i) & 1)

    def get_value(self):
        r = bitarray()
        for pin in self:
            r.append(pin.get_value())
        return r

class Device:
    def __init__(self, irlen, max_freq=None, idcode=None, opcodes=None, cells=[]):
        self.irlen = irlen
        self.max_freq = max_freq
        self.idcode = idcode
        if opcodes is None: opcodes = {'BYPASS': bitarray('1' * irlen)}
        if not 'BYPASS' in opcodes: raise ValueError("BYPASS command is required")
        self.opcodes = opcodes
        self.cells = cells
        self.pinmap = {}
        for cell in self.cells:
            if cell.port != "*":
                try:
                    pin = self.pinmap[cell.port]
                except KeyError:
                    pin = Pin(cell.port)
                    self.pinmap[cell.port] = pin

                if cell.function == "output3" or cell.function == "bidir":
                    pin.output_cell = cell
                    if not cell.ctl_cell is None:
                        pin.control_cell = self.cells[cell.ctl_cell]
                if cell.function == "input" or cell.function == "bidir":
                    pin.input_cell = cell

    def update_br(self, br):
        if len(br) != len(self.cells): raise ValueError("Invalid br length")
        for i, v in enumerate(br):
            self.cells[i].in_value = v

    def generate_br(self):
        r = bitarray()
        for cell in self.cells:
            r.append(cell.out_value)
        return r

    @staticmethod
    def from_bsdl(fn):
        with open(fn, "rt") as f:
            bsdi_file = BSDLFile.parse(f)

        max_freq = float(bsdi_file.attributes["TAP_SCAN_CLOCK"].value)

        irlen = int(bsdi_file.attributes['INSTRUCTION_LENGTH'].value)
        idcode = StdLogicPattern(bsdi_file.attributes['IDCODE_REGISTER'].value[::-1])

        opcodes = {}
        opcode_str = bsdi_file.attributes['INSTRUCTION_OPCODE'].value
        while True:
            m = RE_OPCODE.match(opcode_str)
            if m:
                opcode = m['opcode'].split(",")
                if len(opcode) == 1:
                    ba = bitarray(opcode[0].strip())
                    ba.reverse()
                    opcodes[m['instruction'].upper()] = ba
                else:
                    # not supported
                    pass
                opcode_str = opcode_str[m.end():]
            else:
                break
        if len(opcode_str) != 0: raise Exception("Invalid INSTRUCTION_OPCODE format")

        brlen = int(bsdi_file.attributes['BOUNDARY_LENGTH'].value)

        cells = [None] * brlen
        cell_str = bsdi_file.attributes['BOUNDARY_REGISTER'].value.strip()
        while True:
            m = RE_CELL.match(cell_str)
            if m:
                cell = Cell.parse(int(m['index']), m['config'])
                cells[cell.num] = cell
                cell_str = cell_str[m.end():]
            else:
                break
        if len(cell_str) != 0: raise Exception("Invalid BOUNDARY_REGISTER format")

        return Device(irlen=irlen, max_freq=max_freq, idcode=idcode, opcodes=opcodes, cells=cells)
