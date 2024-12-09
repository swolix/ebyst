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

from .bsdl import BSDLReader

SPACE = "[ \r\n\t]*"

RE_OPCODE = re.compile(f"{SPACE}(?P<instruction>[A-Za-z][A-Za-z_0-9]*){SPACE}\\((?P<opcode>[01]+(,{SPACE}[01]+)*)\\){SPACE}(,)?")
RE_CELL = re.compile(f"{SPACE}(?P<index>[0-9]+){SPACE}\\((?P<format>([^\\)\\(]*(\\([^\\)]*\\))*)*)\\)({SPACE},)?")

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

        self.set_safe()

    def set_safe(self):
        if self.safe.upper() != 'X':
            self.value = int(self.safe)

    def __repr__(self):
        return f"{self.cell} @ {self.num}"

    @classmethod
    def parse(cls, num, parameters):
        return cls(num, *[p.strip() for p in parameters.split(",")])

class Pin:
    """Represents a pin with control & data cell"""
    def __init__(self, name, data_cell, control_cell):
        self.name = name
        self.data_cell = data_cell
        self.control_cell = control_cell

    def output_enabled(self):
        if self.data_cell.cell != "BC_7" or self.control_cell.cell != "BC_2": raise Exception("Not supported")
        return self.control_cell.value != self.data_cell.out_dis_ctl
    
    def output_enable(self, enable=True):
        if self.data_cell.cell != "BC_7" or self.control_cell.cell != "BC_2": raise Exception("Not supported")
        if enable:
            self.control_cell.value = [1, 0][self.data_cell.out_dis_ctl]
        else:
            self.control_cell.value = self.data_cell.out_dis_ctl

    def set_value(self, value):
        if self.data_cell.cell != "BC_7" or self.control_cell.cell != "BC_2": raise Exception("Not supported")
        self.data_cell.value = 1 if value else 0

    def __repr__(self):
        if self.output_enabled():
            return f"<PIN {self.name}: output: {self.data_cell.value}>"
        else:
            return f"<PIN {self.name}: input>: {self.data_cell.value}>"

class Device:
    def __init__(self, irlen, idcode=None, opcodes=None, cells=[]):
        self.irlen = irlen
        self.idcode = idcode
        if opcodes is None: opcodes = {'BYPASS': bitarray('1' * irlen)}
        if not 'BYPASS' in opcodes: raise ValueError("BYPASS command is required")
        self.opcodes = opcodes
        self.cells = cells
        self.pinmap = {}
        for cell in self.cells:
            if cell.port != "*":
                pin = Pin(cell.port, cell, self.cells[cell.ctl_cell] if not cell.ctl_cell is None else None)
                self.pinmap[pin.name] = pin

    def update_br(self, br):
        if len(br) != len(self.cells): raise ValueError("Invalid br length")
        for i, v in enumerate(br):
            self.cells[i].value = v

    def generate_br(self):
        r = bitarray()
        for cell in self.cells:
            r.append(cell.value)
        return r

    @staticmethod
    def from_bsdl(fn):
        with open(fn, "rt") as f:
            attributes = BSDLReader.parse(f)

        irlen = int(attributes['INSTRUCTION_LENGTH'])
        idcode = StdLogicPattern(attributes['IDCODE_REGISTER'][-2:0:-1])

        opcodes = {}
        opcode_str = attributes['INSTRUCTION_OPCODE'][1:-1]
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

        brlen = int(attributes['BOUNDARY_LENGTH'])

        cells = [None] * brlen
        cell_str = attributes['BOUNDARY_REGISTER'][1:-1].strip()
        while True:
            m = RE_CELL.match(cell_str)
            if m:
                cell = Cell.parse(int(m['index']), m['format'])
                cells[cell.num] = cell
                cell_str = cell_str[m.end():]
            else:
                break
        if len(cell_str) != 0: raise Exception("Invalid BOUNDARY_REGISTER format")

        return Device(irlen=irlen, idcode=idcode, opcodes=opcodes, cells=cells)
