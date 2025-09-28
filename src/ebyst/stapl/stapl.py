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

from .expressions import Expression
from .data import IntegerVariable, IntegerArrayVariable, BoolVariable, BoolArrayVariable, Evaluatable, Int, Bool, VariableScope

from pprint import pprint

logger = logging.getLogger(__name__)

class ExitCode(Exception):
    def __init__(self, code=0):
        self.code = code

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

class VariableDecl:
    def __init__(self,  _s, _loc, tokens):
        self.name = tokens[0]
        if len(tokens) > 1:
            self.length = tokens[1].evaluate()
        else:
            self.length = None

    def __repr__(self):
        if self.length is None:
            return f"<{self.name}>"
        else:
            return f"<{self.name}[{self.length}]>"

class Instruction:
    def __init__(self,  s, loc, tokens):
        self.loc = loc

    def execute(self, interpreter):
        raise NotImplementedError(f"{type(self)} not implemented")

class LabelledInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert len(tokens) == 2
        self.label = tokens[0][0] if len(tokens[0]) > 0 else None
        self.instruction = tokens[1]

    def execute(self, interpreter):
        return self.instruction.execute(interpreter)

class Assignment(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        if len(tokens) == 2:
            self.variable = tokens[0]
            self.first = None
            self.last = None
            self.value = tokens[1]
        elif len(tokens) == 3:
            self.variable = tokens[0]
            self.first = tokens[1]
            self.last = None
            self.value = tokens[2]
        elif len(tokens) == 4:
            self.variable = tokens[0]
            self.first = tokens[1]
            self.last = tokens[2]
            self.value = tokens[3]
        else:
            print(tokens)
            assert False

    def execute(self, interpreter):
        v = self.value.evaluate(interpreter.scope)
        if not self.last is None:
            first = self.first.evaluate()
            last = self.last.evaluate()
            length = last - first + 1 if last > first else first - last + 1
            if last - first + 1 != len(v):
                raise ValueError(f"Can't assign slice of length {len(v)} to slice of length {length}")
            logger.debug(f"Setting {self.variable}[{first}] to {v}...")
            interpreter.scope[self.variable].assign(first, v)
        elif not self.first is None:
            first = self.first.evaluate()
            logger.debug(f"Setting {self.variable}[{first}] to {v}...")
            interpreter.scope[self.variable].assign(first, v)
        else:
            logger.debug(f"Setting {self.variable} to {v}...")
            interpreter.scope[self.variable].assign(v)

class BooleanInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.name = tokens[0].name
        self.length = None if tokens[0].length is None else int(tokens[0].length.evaluate())

        if not self.length is None:
            self.value = [None] * self.length
            if len(tokens) > 1:
                assert self.length == len(tokens) - 1
                for i in range(self.length):
                    self.value[i] = tokens[i+1]
        else:
            self.value = None
            if len(tokens) > 1:
                assert 1 == len(tokens) - 1
                self.value = tokens[1]

    def execute(self, interpreter):
        if self.length is None:
            interpreter.scope[self.name] = var = BoolVariable()

            if not self.value is None:
                v2 = self.value.evaluate(interpreter.scope)
                logger.debug(f"Setting {self.name} to {v2}...")
                var.assign(v2)
        else:
            interpreter.scope[self.name] = var = BoolArrayVariable(self.length)

            if not self.value is None:
                for i in range(self.length):
                    v = self.value[i].evaluate(interpreter.scope)
                    logger.debug(f"Setting {self.name}[{i}] to {v}...")
                    var[i].assign(v)

class CallInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.procedure = tokens[1]

    def execute(self, interpreter):
        interpreter.call(self.procedure)

class DrScanInstruction(Instruction):
    pass

class DrStopInstruction(Instruction):
    pass

class ExitInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.exit_code = tokens[0]

    def execute(self, interpreter):
        raise ExitCode(self.exit_code.evaluate(interpreter.scope))

class ExportInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.key = tokens[0]
        self.parts = tokens[1:]

    def execute(self, interpreter):
        s = ""
        for part in self.parts:
            if isinstance(part, Evaluatable):
                s += str(part.evaluate(interpreter.scope))
            else:
                s += str(part)
        logger.info(f"EXPORT {self.key}: {s}")
        interpreter.ctl.export(self.key, s)

    def __repr__(self):
        return f"EXPORT {', '.join(str(s) for s in self.parts)}"

class FrequencyInstruction(Instruction):
    pass

class GotoInstruction(Instruction):
    pass

class IfInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.condition = tokens[0]
        self.instruction = tokens[1]

    def execute(self, interpreter):
        v = self.condition.evaluate(interpreter.scope)
        if Bool(v):
            self.instruction.execute(interpreter)

class IntegerInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.name = tokens[0].name
        self.length = None if tokens[0].length is None else int(tokens[0].length.evaluate())

        if not self.length is None:
            self.value = [None] * self.length
            if len(tokens) > 1:
                assert self.length == len(tokens) - 1
                for i in range(self.length):
                    self.value[i] = tokens[i+1]
        else:
            self.value = None
            if len(tokens) > 1:
                assert 1 == len(tokens) - 1
                self.value = tokens[1]

    def execute(self, interpreter):
        if self.length is None:
            interpreter.scope[self.name] = var = IntegerVariable()

            if not self.value is None:
                v2 = self.value.evaluate(interpreter.scope)
                logger.debug(f"Setting {self.name} to {v2}...")
                var.assign(v2)
        else:
            interpreter.scope[self.name] = var = IntegerArrayVariable(self.length)

            if not self.value is None:
                for i in range(self.length):
                    v = self.value[i].evaluate(interpreter.scope)
                    logger.debug(f"Setting {self.name}[{i}] to {v}...")
                    var[i].assign(v)

class IrScanInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.length = tokens[0]
        self.value = tokens[1]

    def execute(self, interpreter):
        logger.debug(f"Loading {self.value.evaluate(interpreter.scope)} into IR")

class IrStopInstruction(Instruction):
    pass

class PopInstruction(Instruction):
    pass

class PrintInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.parts = tokens

    def execute(self, interpreter):
        s = ""
        for part in self.parts:
            if isinstance(part, Expression):
                s += str(part.evaluate(interpreter.scope))
            else:
                s += str(part)
        print(s)

    def __repr__(self):
        return f"PRINT {', '.join(str(s) for s in self.parts)}"

class PushInstruction(Instruction):
    pass

class StateInstruction(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        self.states = tokens
        if not self.states[-1].upper() in ("RESET", "IDLE", "DRPAUSE", "IRPAUSE"):
            raise Exception("State must end in one of RESET, IDLE, DRPAUSE, IRPAUSE")

    def execute(self, interpreter):
        for state in self.states:
            logger.debug(f"Entering state {state}...")
        logger.warning(f"Instruction not implemented")

class TRSTInstruction(Instruction):
    pass

class WaitInstruction(Instruction):
    pass

class For(Instruction):
    def __init__(self,  s, loc, tokens):
        Instruction.__init__(self, s, loc, tokens)
        assert tokens[0][0] == tokens[2][1]
        self.var = tokens[0][0]
        self.start = tokens[0][1]
        self.end = tokens[0][2]
        self.step = tokens[0][3] if len(tokens[0]) == 4 else Int(1)
        self.statements = tokens[1]

    def execute(self, interpreter):
        start = self.start.evaluate(interpreter.scope)
        step = self.step.evaluate(interpreter.scope)
        end = self.end.evaluate(interpreter.scope)
        interpreter.scope[self.var] = var = IntegerVariable()
        var.assign(start)
        while True:
            for statement in self.statements:
                statement.execute(interpreter)
            var += step
            if Int(step) > 0 and var >= end:
                break
            elif Int(step) < 0 and var <= end:
                break

class Procedure:
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 3
        self.enter_label = tokens[0][0][0] if len(tokens[0][0]) > 0 else None
        self.name = tokens[0][1]
        self.uses = tokens[0][2]
        self.statements = tokens[1]
        self.exit_label = tokens[2][0][0] if len(tokens[2][0]) > 0 else None
        print("BBB", self.statements[0])

    def __repr__(self):
        return f"<Procedure {self.name} ({len(self.statements)} statements)>"

    def execute(self, interpreter):
        for statement in self.statements:
            statement.execute(interpreter)

class Data:
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 3
        assert len(tokens[0]) >= 2
        self.name = tokens[0][1]
        self.statements = tokens[1][0]

    def execute(self, interpreter):
        for statement in self.statements:
            statement.execute(interpreter)

    def __repr__(self):
        return f"<Data {self.name} ({len(self.statements)} statements)>"

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

class Interpreter:
    def __init__(self, ctl, stapl):
        self.stapl = stapl
        self.ctl = ctl
        self.call_stack = []
        self.data_scopes = {}
        self.scope = None

    def call(self, procedure):
        assert isinstance(procedure, str)
        procedure = self.stapl.procedures[procedure]
        self.call_stack.append(self.scope)
        self.scope = VariableScope()

        for dep in procedure.uses:
            subproc = self.stapl.procedures.get(dep)
            data = self.data_scopes.get(dep)
            if not (data is None or subproc is None):
                raise Exception(f"{dep} defined multuple times")
            elif data is None and subproc is None:
                raise Exception(f"{dep} not found")
            if not data is None:
                for k, v in data.items():
                    self.scope[k] = v

        procedure.execute(self)
        self.scope = self.call_stack.pop()

    def run(self, action):
        for name, data in self.stapl.data_blocks.items():
            self.scope = VariableScope()
            data.execute(self)
            self.data_scopes[name] = self.scope
            self.scope = None

        try:
            action = self.stapl.actions[action]
        except KeyError:
            raise KeyError(f"Action {action} not found")
        for procedure, opt in action.procedures:
            try:
                self.call(procedure)
            except KeyError:
                raise KeyError(f"Procedure {procedure} not found")

class StaplFile:
    """STAPL parser"""

    def __init__(self,  tokens):
        self.actions = {}
        self.procedures = {}
        self.data_blocks = {}
        self.notes = []
        for token in tokens:
            if isinstance(token, Note):
                logger.info(f"NOTE: {token}")
                self.notes.append(token)
            elif isinstance(token, Action):
                logger.debug(f"Action: {token.name}")
                self.actions[token.name] = token
            elif isinstance(token, Procedure):
                logger.debug(f"Procedure: {token.name}")
                self.procedures[token.name] = token
            elif isinstance(token, Data):
                logger.debug(f"Data: {token.name}")
                self.data_blocks[token.name] = token
            elif isinstance(token, Crc):
                if not token.is_correct():
                    logger.warning(f"CRC check failed ({token.actual:04x}, expected: {token.expected:04x})")
            else:
                assert False

    def execute(self, ctl, action):
        interpreter = Interpreter(ctl, self)
        interpreter.run(action)

    @classmethod
    def parse(cls, f):
        comments = "`" + pp.SkipTo(pp.LineEnd())
        proc_instruction = pp.Forward()

        expression = Expression.get_parse_rule()
        identifier = pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]"))
        variable_decl = (identifier + pp.Opt(pp.Literal("[").suppress() - expression - pp.Literal("]").suppress())).set_parse_action(VariableDecl)

        str_expression = pp.Or((pp.QuotedString("\""), expression)) # TODO

        action = (pp.CaselessKeyword("ACTION").suppress() - identifier - pp.Group(pp.Opt(pp.QuotedString("\""))) -
                  pp.Literal("=").suppress() -
                  pp.Group(identifier - pp.Or((pp.CaselessKeyword("OPTIONAL") + pp.Tag("opt", "optional"),
                                               pp.CaselessKeyword("RECOMMENDED") + pp.Tag("opt", "recommended"),
                                               pp.Tag("opt", "required")))) -
                  pp.ZeroOrMore(pp.Literal(",").suppress() - pp.Group(identifier -
                                pp.Or((pp.CaselessKeyword("OPTIONAL") + pp.Tag("opt", "optional"),
                                       pp.CaselessKeyword("RECOMMENDED") + pp.Tag("opt", "recommended"),
                                       pp.Tag("opt", "required"))))) -
                  pp.Literal(";").suppress()).set_parse_action(Action)
        variable = (pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]")) +
                    pp.Opt(pp.Literal("[").suppress() + pp.Opt(expression + pp.Opt(pp.Literal("..").suppress() + expression)) +
                           pp.Literal("]").suppress()))
        assignment = (variable + pp.Literal("=").suppress() + expression + pp.Suppress(pp.Literal(";"))).set_parse_action(Assignment)
        boolean = (pp.CaselessKeyword("BOOLEAN").suppress() - variable_decl -
                           pp.Opt(pp.Literal("=").suppress() - expression - pp.ZeroOrMore(pp.Literal(",").suppress() - expression)) - pp.Literal(";").suppress()).set_parse_action(BooleanInstruction)
        call = (pp.CaselessKeyword("CALL") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(CallInstruction)
        crc = (pp.CaselessKeyword("CRC").suppress() - pp.Word(pp.srange("[0-9a-fA-F]")) - pp.Literal(";").suppress()).set_parse_action(Crc)
        drscan = (pp.CaselessKeyword("DRSCAN").suppress() - expression - pp.Literal(",").suppress() - expression -
                          pp.Opt(pp.Literal(",").suppress() + pp.CaselessKeyword("CAPTURE") - expression) -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Literal(",").suppress() - expression + pp.Literal(",").suppress() - expression) -
                          pp.Literal(";").suppress()).set_parse_action(DrScanInstruction)
        drstop = (pp.CaselessKeyword("DRSTOP") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(DrStopInstruction)
        exit = (pp.CaselessKeyword("EXIT").suppress() - expression - pp.Suppress(pp.Literal(";"))).set_parse_action(ExitInstruction)
        export = (pp.CaselessKeyword("EXPORT").suppress() - str_expression -
                  pp.ZeroOrMore(pp.Suppress(pp.Literal(",")) - str_expression) - pp.Literal(";").suppress()).set_parse_action(ExportInstruction)
        for_ = pp.Forward()
        frequency = (pp.CaselessKeyword("FREQUENCY").suppress() - pp.Opt(expression) - pp.Literal(";").suppress()).set_parse_action(FrequencyInstruction)
        goto = (pp.CaselessKeyword("GOTO") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(GotoInstruction)
        if_ = (pp.CaselessKeyword("IF").suppress() - expression - pp.CaselessKeyword("THEN").suppress() - proc_instruction).set_parse_action(IfInstruction)
        integer = (pp.CaselessKeyword("INTEGER").suppress() - variable_decl -
                           pp.Opt(pp.Literal("=").suppress() - expression - pp.ZeroOrMore(pp.Literal(",").suppress() - expression)) - pp.Literal(";").suppress()).set_parse_action(IntegerInstruction)
        irscan = (pp.CaselessKeyword("IRSCAN").suppress() - expression + pp.Literal(",").suppress() - expression -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("CAPTURE") - expression) -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Literal(",").suppress() - expression - pp.Literal(",").suppress() - expression) -
                          pp.Suppress(pp.Literal(";"))).set_parse_action(IrScanInstruction)
        irstop = (pp.CaselessKeyword("IRSTOP") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(IrStopInstruction)
        note = (pp.CaselessKeyword("NOTE").suppress() - pp.QuotedString("\"") - pp.QuotedString("\"") - pp.Literal(";").suppress()).set_parse_action(Note)
        pop = ((pp.CaselessKeyword("POP") - identifier - pp.Suppress(pp.Literal(";")))).set_parse_action(PopInstruction)
        # postdr = ((pp.CaselessKeyword("POSTDR") - pp.Suppress(pp.Literal(";")))) # TODO
        # postir = (pp.CaselessKeyword("POSTIR") - pp.Suppress(pp.Literal(";"))) # TODO
        # predr = (pp.CaselessKeyword("PREDR") - pp.Suppress(pp.Literal(";"))) # TODO
        # preir = (pp.CaselessKeyword("PREIR") - pp.Suppress(pp.Literal(";"))) # TODO
        print_ = (pp.CaselessKeyword("PRINT").suppress() - str_expression -
                  pp.ZeroOrMore(pp.Suppress(pp.Literal(",")) - str_expression) - pp.Literal(";").suppress()).set_parse_action(PrintInstruction)
        push = (pp.CaselessKeyword("PUSH") - expression - pp.Suppress(pp.Literal(";"))).set_parse_action(PushInstruction)
        state = (pp.CaselessKeyword("STATE").suppress() - pp.OneOrMore(identifier) - pp.Literal(";").suppress()).set_parse_action(StateInstruction)
        wait_type = pp.Or((expression - pp.CaselessKeyword("CYCLES") -
                           pp.Opt(pp.Suppress(pp.Literal(",")) - expression - pp.CaselessKeyword("USEC")),
                           expression - pp.CaselessKeyword("USEC")))
        trst = (pp.CaselessKeyword("TRST") - wait_type - pp.Suppress(pp.Literal(";"))).set_parse_action(TRSTInstruction)
        wait = (pp.CaselessKeyword("WAIT") - pp.Opt(identifier - pp.Suppress(pp.Literal(","))) -
                        wait_type - pp.Opt(pp.Suppress(pp.Literal(",")) - identifier) -
                        pp.Opt(pp.CaselessKeyword("MAX") - wait_type) - pp.Suppress(pp.Literal(";"))).set_parse_action(WaitInstruction)

        opt_label = pp.Group(pp.Opt(identifier + pp.Suppress(pp.Literal(":"))))
        proc_instruction <<= pp.Or((assignment, boolean, call, crc, drscan, drstop, exit, export, for_, frequency,
                                    goto, if_, integer, irscan, irstop, note, pop, print_, push, state, trst, wait))
        proc_statement = (opt_label + proc_instruction).set_parse_action(LabelledInstruction)
        data_statement = pp.Or((boolean, integer))

        data = (pp.Group(opt_label + pp.CaselessKeyword("DATA").suppress() - identifier - pp.Suppress(pp.Literal(";"))) -
                pp.Group(pp.ZeroOrMore(pp.Group(data_statement))) -
                pp.Group(opt_label - pp.CaselessKeyword("ENDDATA").suppress() - pp.Literal(";").suppress())).set_parse_action(Data)
        procedure = (pp.Group(opt_label + pp.CaselessKeyword("PROCEDURE").suppress() - identifier -
                              pp.Group(pp.Opt(pp.CaselessKeyword("USES").suppress() - identifier -
                                       pp.ZeroOrMore(pp.Literal(",").suppress() - identifier))) - pp.Literal(";").suppress()) -
                              pp.Group(pp.ZeroOrMore(proc_statement)) -
                              pp.Group(opt_label - pp.CaselessKeyword("ENDPROC").suppress() - pp.Literal(";").suppress())).set_parse_action(Procedure)
        for_ <<= (pp.Group(pp.CaselessKeyword("FOR").suppress() - identifier - pp.Literal("=").suppress() -
                           expression - pp.CaselessKeyword("TO").suppress() - expression -
                           pp.Opt(pp.CaselessKeyword("STEP").suppress() - expression) - pp.Suppress(pp.Literal(";"))) -
                  pp.Group(pp.ZeroOrMore(proc_statement)) -
                  pp.Group(opt_label - pp.CaselessKeyword("NEXT").suppress() - identifier - pp.Literal(";").suppress())).set_parse_action(For)

        stapl_file = (pp.ZeroOrMore(note) + pp.ZeroOrMore(action) + pp.ZeroOrMore(pp.Or((procedure, data))) +
                      crc + pp.StringEnd())

        stapl_file.ignore(comments)
        stapl_file.enable_packrat()

        return StaplFile(stapl_file.parse_string(f.read()))
