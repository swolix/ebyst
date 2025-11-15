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
import pyparsing as pp

from .data import Int, IntArray
from .expressions import Expression
from ..tap_controller import State

logger = logging.getLogger(__name__)

class Note:
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 2
        self.key = tokens[0]
        self.text = tokens[1]

    def __str__(self):
        return f"{self.key}: {self.text}"

class Action:
    def __init__(self,  _s, _loc, tokens):
        self.name = tokens[0]
        self.text = tokens[1][0] if len(tokens[1]) > 0 else tokens[0]
        self.procedures = []
        for procedure in tokens[2:]:
            self.procedures.append((procedure[0], procedure.opt))

    def __repr__(self):
        return f"<Action {self.text}: {', '.join(p[0] + ("?" if p[1] == "optional" else "") +
                                                 ("*" if p[1] == "recommended" else "") for p in self.procedures)}>"

    def __str__(self):
        return f"ACTION {self.name}"

class VariableDecl:
    def __init__(self,  _s, _loc, tokens):
        self.name = tokens[0]
        if len(tokens) > 1:
            self.length = tokens[1].evaluate()
        else:
            self.length = None

    def __str__(self):
        if self.length is None:
            return f"{self.name}"
        else:
            return f"{self.name}[{self.length}]"

class Variable:
    def __init__(self,  s, loc, tokens):
        if len(tokens) == 1:
            self.name = tokens[0]
            self.first = None
            self.last = None
        elif len(tokens) == 2:
            self.name = tokens[0]
            self.first = tokens[1]
            self.last = None
        elif len(tokens) == 3:
            self.name = tokens[0]
            self.first = tokens[1]
            self.last = tokens[2]
        else:
            assert False

    def __str__(self):
        return self.name

class Instruction:
    def __init__(self,  s, loc, tokens):
        self.line = pp.lineno(loc, s)
        self.col = pp.col(loc, s)

class LabelledInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 2
        self.label = tokens[0][0] if len(tokens[0]) > 0 else None
        self.instruction = tokens[1]

    def execute(self, interpreter):
        return self.instruction.execute(interpreter)

    def __str__(self):
        return f"{self.label}: {self.instruction}"

class AssignmentInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        if len(tokens) == 2:
            self.variable = tokens[0]
            self.value = tokens[1]
        else:
            print(tokens)
            assert False

    def __str__(self):
        return f"{self.variable.name} = {self.value}"

class BooleanInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.name = tokens[0].name
        self.length = None if tokens[0].length is None else int(tokens[0].length.evaluate())
        if len(tokens) > 1:
            self.value = tokens[1]
        else:
            self.value = None

    def __str__(self):
        return f"BOOLEAN {self.name}"

class CallInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 1
        self.procedure = tokens[0]

    def __str__(self):
        return f"CALL {self.procedure}"

class ScanInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.length = tokens[0]
        self.data_array = tokens[1]
        i = 2
        if len(tokens) > i and tokens[i].upper() == "CAPTURE":
            self.capture_array = tokens[i+1]
            i += 2
        else:
            self.capture_array = None
        if len(tokens) > i and tokens[i].upper() == "COMPARE":
            self.compare_array = tokens[i+1]
            self.compare_mask_array = tokens[i+2]
            self.compare_result = tokens[i+3]
            i += 4
        else:
            self.compare_array = None
            self.mask_array = None
            self.compare_result = None
        assert i == len(tokens)

class DrScanInstruction(ScanInstruction):
    def __str__(self):
        return f"DRSCAN {self.length}"

class DrStopInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 1
        self.state = tokens[0].state

    def __str__(self):
        return f"IRSTOP {self.state}"

class ExitInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.exit_code = tokens[0]

    def __str__(self):
        return f"EXIT {self.exit_code}"

class ExportInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.key = tokens[0]
        self.parts = tokens[1:]

    def __repr__(self):
        return f"EXPORT {', '.join(str(s) for s in self.parts)}"

class FrequencyInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.frequency = tokens[0]

    def __str__(self):
        return f"FREQUENCY {self.frequency}"

class GotoInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.label = tokens[1]

    def __str__(self):
        return f"GOTO {self.label}"

class IfInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.condition = tokens[0]
        self.instruction = tokens[1]

    def __str__(self):
        return f"IF {self.condition} THEN {self.instruction}"

class IntegerInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.name = tokens[0].name
        self.length = None if tokens[0].length is None else int(tokens[0].length.evaluate())

        if not self.length is None:
            self.value = IntArray([Int(0)] * self.length)
            if len(tokens) > 1:
                assert self.length == len(tokens) - 1
                for i in range(self.length):
                    self.value[i] = tokens[i+1]
        else:
            self.value = Int(0)
            if len(tokens) > 1:
                assert 1 == len(tokens) - 1
                self.value = tokens[1]

    def __repr__(self):
        if self.length is None:
            return f"<Integer {self.name}>"
        else:
            return f"<Integer {self.name}[{self.length}]>"

    def __str__(self):
        return f"INTEGER {self.name}"

class IrScanInstruction(ScanInstruction):
    def __str__(self):
        return f"IRSCAN {self.length}"

class IrStopInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 1
        self.state = tokens[0].state

    def __str__(self):
        return f"IRSTOP {self.state}"

class PopInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        if len(tokens) == 1:
            self.variable = tokens[0]
        else:
            assert False

    def __str__(self):
        return f"POP {self.variable}"

class PrintInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.parts = tokens

    def __str__(self):
        return f"PRINT {', '.join(str(s) for s in self.parts)}"

class PushInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 1
        self.value = tokens[0]

    def __str__(self):
        return f"PUSH {self.value}"

class StateConvert:
    def __init__(self,  s, loc, tokens):
        assert len(tokens) == 1
        if tokens[0] == "RESET":
            self.state = State.TEST_LOGIC_RESET
        elif tokens[0] == "IDLE":
            self.state = State.RUN_TEST_IDLE
        elif tokens[0] == "DRSELECT":
            self.state = State.SELECT_DR_SCAN
        elif tokens[0] == "DRCAPTURE":
            self.state = State.CAPTURE_DR
        elif tokens[0] == "DRSHIFt":
            self.state = State.SHIFT_DR
        elif tokens[0] == "DREXIT1":
            self.state = State.EXIT1_DR
        elif tokens[0] == "DRPAUSE":
            self.state = State.PAUSE_DR
        elif tokens[0] == "DREXIT2":
            self.state = State.EXIT2_DR
        elif tokens[0] == "DRUPDATE":
            self.state = State.UPDATE_DR
        elif tokens[0] == "IRSELECT":
            self.state = State.SELECT_IR_SCAN
        elif tokens[0] == "IRCAPTURE":
            self.state = State.CAPTURE_IR
        elif tokens[0] == "IRSHIFT":
            self.state = State.SHIFT_IR
        elif tokens[0] == "IREXIT1":
            self.state = State.EXIT1_IR
        elif tokens[0] == "IRPAUSE":
            self.state = State.PAUSE_IR
        elif tokens[0] == "IREXIT2":
            self.state = State.EXIT2_IR
        elif tokens[0] == "IRUPDATE":
            self.state = State.UPDATE_IR
        else:
            assert False

class StateInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.states = [token.state for token in tokens]

    def __str__(self):
        return f"STATE {', '.join(str(s) for s in self.states)}"

class WaitType:
    def __init__(self,  s, loc, tokens):
        self.usec = self.cycles = Int(0)
        if len(tokens) == 2 and tokens[1].upper() == "USEC":
            self.usec = tokens[0]
        elif len(tokens) == 2 and tokens[1].upper() == "CYCLES":
            self.cycles = tokens[0]
        elif len(tokens) == 4 and tokens[1].upper() == "CYCLES" and tokens[3].upper() == "USEC":
            self.cycles = tokens[0]
            self.usec = tokens[2]
        else:
            assert False

    def __str__(self):
        return f"{self.cycles} CYCLES {self.usec} USEC"

class TRSTInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        if len(tokens) == 0:
            self.wait_cycles = self.wait_usec = Int(0)
        elif len(tokens) == 1:
            self.wait_cycles = tokens[0].cycles
            self.wait_usec = tokens[0].usec
        else:
            assert False

    def __str__(self):
        return f"TRST {self.wait_cycles} CYCLES {self.wait_usec} USEC"

class WaitInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)

        self.wait_state = self.end_state = None
        self.wait_usec = self.wait_cycles = Int(0)

        i = 0
        if len(tokens) > i and not isinstance(tokens[i], WaitType):
            self.wait_state = tokens[i].state
            i += 1

        if len(tokens) > i and isinstance(tokens[i], WaitType):
            self.wait_cycles = tokens[i].cycles
            self.wait_usec = tokens[i].usec
            i += 1
        else:
            assert False

        if len(tokens) > i and not isinstance(tokens[i], WaitType):
            self.end_state = tokens[i].state
            i += 1

        if len(tokens) > i and isinstance(tokens[i], WaitType):
            raise Exception("MAX wait times are not supported")

        assert i == len(tokens)

    def __str__(self):
        r = "WAIT"
        if not self.wait_state is None:
            r += f" {self.wait_state}"
        r += f" {self.wait_cycles} CYCLES {self.wait_usec} USEC"
        if not self.wait_state is None:
            r += f" {self.end_state}"
        return r

class ForInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 3 or len(tokens) == 4
        self.var = tokens[0]
        self.start = tokens[1]
        self.end = tokens[2]
        self.step = tokens[3] if len(tokens) == 4 else Int(1)

    def __str__(self):
        return f"FOR {self.var} = {self.start}..{self.end} STEP {self.step}"

class NextInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 1
        self.var = tokens[0]

    def __str__(self):
        return f"NEXT {self.var}"

class ScanModifierInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        if len(tokens) == 1:
            self.bits = tokens[0]
            self.value = None
        elif len(tokens) == 2:
            self.bits = tokens[0]
            self.value = tokens[1]
        else:
            assert False

class PostDrInstruction(ScanModifierInstruction):
    pass

class PostIrInstruction(ScanModifierInstruction):
    pass

class PreDrInstruction(ScanModifierInstruction):
    pass

class PreIrInstruction(ScanModifierInstruction):
    pass

class ProcedureInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 2
        self.name = tokens[0]
        self.uses = tokens[1]

    def __repr__(self):
        return f"<Procedure {self.name}>"

    def __str__(self):
        return f"PROCEDURE {self.name}"

class EndProcedureInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)

    def __str__(self):
        return f"ENDPROC"

class DataInstruction(Instruction):
    def __init__(self, s, loc, tokens):
        assert len(tokens) == 1
        Instruction.__init__(self, s, loc, tokens)
        self.name = tokens[0]

    def __str__(self):
        return f"DATA {self.name}"

class EndDataInstruction(Instruction):
    def __str__(self):
        return f"<ENDDATA>"

class Crc:
    def __init__(self,  s, loc, tokens):
        assert len(tokens) == 1
        self.expected = int(tokens[0], 16)

        if self.expected != 0:
            CCITT_CRC =  0x8408
            crc_register = 0xFFFF
            for in_byte in s[:loc]:
                in_byte = ord(in_byte)
                if in_byte != 13:
                    for _ in range(8):
                        feedback = (in_byte ^ crc_register) & 0x01;
                        crc_register >>= 1; # shift the shift register
                        if feedback: crc_register ^= CCITT_CRC; # invert selected bits
                        in_byte >>= 1; # get the next bit of in_byte

            self.actual = (~crc_register) & 0xFFFF
        else:
            self.actual = 0

    def is_correct(self):
        return self.actual == self.expected

    def __repr__(self):
        if self.is_correct():
            return "<Crc (correct)>"
        else:
            return "<Crc (incorrect)>"

    def __str__(self):
        return f"CRC {self.expected:04x}"

class StaplFile:
    """STAPL parser"""

    def __init__(self,  tokens):
        self.actions = {}
        self.procedures = {}
        self.data_blocks = {}
        self.labels = {}
        self.notes = []
        self.statements = []
        procedure = data_block = None
        for token in tokens:
            if isinstance(token, Note):
                assert data_block is None and procedure is None
                logger.info(f"NOTE: {token}")
                self.notes.append(token)
            elif isinstance(token, Action):
                assert data_block is None and procedure is None
                logger.debug(f"Action: {token.name}")
                self.actions[token.name] = token
            elif isinstance(token, LabelledInstruction):
                if isinstance(token.instruction, ProcedureInstruction):
                    assert data_block is None
                    procedure = token.instruction.name
                    self.procedures[procedure] = len(self.statements)
                    self.labels[procedure] = {}
                elif isinstance(token.instruction, EndProcedureInstruction):
                    procedure = None
                elif isinstance(token.instruction, DataInstruction):
                    assert procedure is None
                    data_block = token.instruction.name
                    self.data_blocks[data_block] = len(self.statements)
                elif isinstance(token.instruction, EndDataInstruction):
                    data_block = None
                if not token.label is None:
                    assert not procedure is None
                    self.labels[procedure][token.label] = len(self.statements)
                self.statements.append(token)
            elif isinstance(token, Crc):
                if not token.is_correct():
                    logger.warning(f"CRC check failed ({token.actual:04x}, expected: {token.expected:04x})")
            else:
                assert False

    @classmethod
    def parse(cls, f):
        comments = "`" + pp.SkipTo(pp.LineEnd())
        instruction = pp.Forward()

        expression = Expression.get_parse_rule()
        identifier = pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]"))
        variable_decl = (identifier + pp.Opt(pp.Literal("[").suppress() - expression - pp.Literal("]").suppress())).set_parse_action(VariableDecl)
        state_name = pp.MatchFirst((pp.CaselessKeyword("RESET"),
                                    pp.CaselessKeyword("IDLE"),
                                    pp.CaselessKeyword("DRSELECT"),
                                    pp.CaselessKeyword("DRCAPTURE"),
                                    pp.CaselessKeyword("DRSHIFT"),
                                    pp.CaselessKeyword("DREXIT1"),
                                    pp.CaselessKeyword("DRPAUSE"),
                                    pp.CaselessKeyword("DREXIT2"),
                                    pp.CaselessKeyword("DRUPDATE"),
                                    pp.CaselessKeyword("IRSELECT"),
                                    pp.CaselessKeyword("IRCAPTURE"),
                                    pp.CaselessKeyword("IRSHIFT"),
                                    pp.CaselessKeyword("IREXIT1"),
                                    pp.CaselessKeyword("IRPAUSE"),
                                    pp.CaselessKeyword("IREXIT2"),
                                    pp.CaselessKeyword("IRUPDATE"))).set_parse_action(StateConvert)

        str_expression = pp.Or((pp.QuotedString("\""), expression)) # TODO

        action = (pp.CaselessKeyword("ACTION").suppress() - identifier - pp.Group(pp.Opt(pp.QuotedString("\""))) -
                  pp.Literal("=").suppress() -
                  pp.Group(identifier - pp.Or((pp.CaselessKeyword("OPTIONAL") - pp.Tag("opt", "optional"),
                                               pp.CaselessKeyword("RECOMMENDED") - pp.Tag("opt", "recommended"),
                                               pp.Tag("opt", "required")))) -
                  pp.ZeroOrMore(pp.Literal(",").suppress() - pp.Group(identifier -
                                pp.Or((pp.CaselessKeyword("OPTIONAL") - pp.Tag("opt", "optional"),
                                       pp.CaselessKeyword("RECOMMENDED") - pp.Tag("opt", "recommended"),
                                       pp.Tag("opt", "required"))))) -
                  pp.Literal(";").suppress()).set_parse_action(Action)
        variable = (pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]")) -
                    pp.Opt(pp.Literal("[").suppress() - pp.Opt(expression - pp.Opt(pp.Literal("..").suppress() - expression)) -
                           pp.Literal("]").suppress())).set_parse_action(Variable)
        assignment = (variable + pp.Literal("=").suppress() - expression - pp.Suppress(pp.Literal(";"))).set_parse_action(AssignmentInstruction)
        boolean = (pp.CaselessKeyword("BOOLEAN").suppress() - variable_decl - pp.Opt(pp.Literal("=").suppress() -
                           expression) - pp.Literal(";").suppress()).set_parse_action(BooleanInstruction)
        call = (pp.CaselessKeyword("CALL").suppress() - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(CallInstruction)
        crc = (pp.CaselessKeyword("CRC").suppress() - pp.Word(pp.srange("[0-9a-fA-F]")) - pp.Literal(";").suppress()).set_parse_action(Crc)
        data = (pp.CaselessKeyword("DATA").suppress() - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(DataInstruction)
        drscan = (pp.CaselessKeyword("DRSCAN").suppress() - expression - pp.Literal(",").suppress() - expression -
                          pp.Opt(pp.Literal(",").suppress() + pp.CaselessKeyword("CAPTURE") - variable) -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Literal(",").suppress() - expression + pp.Literal(",").suppress() - variable) -
                          pp.Literal(";").suppress()).set_parse_action(DrScanInstruction)
        drstop = (pp.CaselessKeyword("DRSTOP").suppress() - state_name - pp.Suppress(pp.Literal(";"))).set_parse_action(DrStopInstruction)
        end_data = (pp.CaselessKeyword("ENDDATA").suppress() - pp.Literal(";").suppress()).set_parse_action(EndDataInstruction)
        end_procedure = (pp.CaselessKeyword("ENDPROC").suppress() - pp.Literal(";").suppress()).set_parse_action(EndProcedureInstruction)
        exit = (pp.CaselessKeyword("EXIT").suppress() - expression - pp.Suppress(pp.Literal(";"))).set_parse_action(ExitInstruction)
        export = (pp.CaselessKeyword("EXPORT").suppress() - str_expression -
                  pp.ZeroOrMore(pp.Suppress(pp.Literal(",")) - str_expression) - pp.Literal(";").suppress()).set_parse_action(ExportInstruction)
        for_ = (pp.CaselessKeyword("FOR").suppress() - identifier - pp.Literal("=").suppress() - expression -
                pp.CaselessKeyword("TO").suppress() - expression -
                pp.Opt(pp.CaselessKeyword("STEP").suppress() - expression) - pp.Suppress(pp.Literal(";"))).set_parse_action(ForInstruction)
        frequency = (pp.CaselessKeyword("FREQUENCY").suppress() - pp.Opt(expression) - pp.Literal(";").suppress()).set_parse_action(FrequencyInstruction)
        goto = (pp.CaselessKeyword("GOTO") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(GotoInstruction)
        if_ = (pp.CaselessKeyword("IF").suppress() - expression - pp.CaselessKeyword("THEN").suppress() - instruction).set_parse_action(IfInstruction)
        integer = (pp.CaselessKeyword("INTEGER").suppress() - variable_decl -
                           pp.Opt(pp.Literal("=").suppress() - expression - pp.ZeroOrMore(pp.Literal(",").suppress() - expression)) - pp.Literal(";").suppress()).set_parse_action(IntegerInstruction)
        irscan = (pp.CaselessKeyword("IRSCAN").suppress() - expression - pp.Literal(",").suppress() - expression -
                          pp.Opt(pp.Literal(",").suppress() + pp.CaselessKeyword("CAPTURE") - variable) -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Literal(",").suppress() - expression + pp.Literal(",").suppress() - variable) -
                          pp.Literal(";").suppress()).set_parse_action(IrScanInstruction)
        irstop = (pp.CaselessKeyword("IRSTOP").suppress() - state_name - pp.Suppress(pp.Literal(";"))).set_parse_action(IrStopInstruction)
        next =  (pp.CaselessKeyword("NEXT").suppress() - identifier - pp.Literal(";").suppress()).set_parse_action(NextInstruction)
        note = (pp.CaselessKeyword("NOTE").suppress() - pp.QuotedString("\"") - pp.QuotedString("\"") - pp.Literal(";").suppress()).set_parse_action(Note)
        pop = ((pp.CaselessKeyword("POP").suppress() - variable - pp.Suppress(pp.Literal(";")))).set_parse_action(PopInstruction)
        postdr = ((pp.CaselessKeyword("POSTDR").suppress() - expression - pp.Opt(pp.Literal(",") - expression) - pp.Literal(";").suppress())).set_parse_action(PostDrInstruction)
        postir = ((pp.CaselessKeyword("POSTIR").suppress() - expression - pp.Opt(pp.Literal(",") - expression) - pp.Literal(";").suppress())).set_parse_action(PostIrInstruction)
        predr = ((pp.CaselessKeyword("PREDR").suppress() - expression - pp.Opt(pp.Literal(",") - expression) - pp.Literal(";").suppress())).set_parse_action(PreDrInstruction)
        preir = ((pp.CaselessKeyword("PREIR").suppress() - expression - pp.Opt(pp.Literal(",") - expression) - pp.Literal(";").suppress())).set_parse_action(PreIrInstruction)
        print_ = (pp.CaselessKeyword("PRINT").suppress() - str_expression -
                  pp.ZeroOrMore(pp.Suppress(pp.Literal(",")) - str_expression) - pp.Literal(";").suppress()).set_parse_action(PrintInstruction)
        procedure = (pp.CaselessKeyword("PROCEDURE").suppress() - identifier -
                     pp.Group(pp.Opt(pp.CaselessKeyword("USES").suppress() - identifier - pp.ZeroOrMore(pp.Literal(",").suppress() - identifier))) -
                     pp.Literal(";").suppress()).set_parse_action(ProcedureInstruction)
        push = (pp.CaselessKeyword("PUSH").suppress() - expression - pp.Suppress(pp.Literal(";"))).set_parse_action(PushInstruction)
        state = (pp.CaselessKeyword("STATE").suppress() - pp.OneOrMore(state_name) - pp.Literal(";").suppress()).set_parse_action(StateInstruction)
        wait_type = pp.Or((expression - pp.CaselessKeyword("CYCLES") -
                           pp.Opt(pp.Suppress(pp.Literal(",")) + expression + pp.CaselessKeyword("USEC")),
                           expression - pp.CaselessKeyword("USEC"))).set_parse_action(WaitType)
        trst = (pp.CaselessKeyword("TRST").suppress() - pp.Opt(wait_type) - pp.Suppress(pp.Literal(";"))).set_parse_action(TRSTInstruction)
        wait = (pp.CaselessKeyword("WAIT").suppress() - pp.Opt(state_name - pp.Suppress(pp.Literal(","))) -
                        wait_type - pp.Opt(pp.Suppress(pp.Literal(",")) - state_name) -
                        pp.Opt(pp.CaselessKeyword("MAX").suppress() - wait_type) - pp.Suppress(pp.Literal(";"))).set_parse_action(WaitInstruction)

        opt_label = pp.Group(pp.Opt(identifier + pp.Suppress(pp.Literal(":"))))
        instruction <<= pp.MatchFirst((assignment, boolean, call, data, drscan, drstop, end_data, end_procedure, exit,
                                       export, for_, frequency, goto, if_, integer, irscan, irstop, next, note, pop,
                                       print_, procedure, push, state, trst, wait))
        statement = (opt_label + instruction).set_parse_action(LabelledInstruction)

        stapl_file = (pp.ZeroOrMore(note) - pp.ZeroOrMore(action) - pp.ZeroOrMore(statement) - crc - pp.StringEnd())

        stapl_file.ignore(comments)
        stapl_file.enable_packrat()

        logger.debug(f"Parsing stapl...")
        f = StaplFile(stapl_file.parse_string(f.read()))
        logger.debug(f"Stapl loaded")
        return f
