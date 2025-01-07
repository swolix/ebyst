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

from pprint import pprint

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

class VariableDecl:
    def __init__(self,  _s, _loc, tokens):
        self.name = tokens[0]
        if len(tokens) > 1:
            self.length = tokens[1].evaluate()
        else:
            self.length = None

    def evaluate(self, scope={}):
        assert False

    def __repr__(self):
        if self.length is None:
            return f"<{self.name}>"
        else:
            return f"<{self.name}[{self.length}]>"

class Expression:
    def __init__(self,  _s, _loc, tokens):
        self.v = tokens

    def evaluate(self, scope={}):
        if len(self.v) == 1:
            if isinstance(self.v[0], int) or isinstance(self.v[0], str):
                return self.v[0]
            elif isinstance(self.v[0], Expression):
                return self.v[0].evaluate(scope)
        elif len(self.v) == 2:
            if self.v[1] == "!":
                assert False
            elif self.v[1] == "~":
                assert False
            elif self.v[0] == "BOOL":
                return True if self.v[1].evaluate(scope) else False
            elif self.v[0] == "INT":
                return int(self.v[1].evaluate(scope))
            elif self.v[0] == "CHR$":
                return chr(self.v[1].evaluate(scope))
            else:
                assert False
        elif len(self.v) == 3:
            if self.v[1] == "*":
                return self.v[0].evaluate() * self.v[2].evaluate()
            elif self.v[1] == "/":
                return self.v[0].evaluate() // self.v[2].evaluate()
            elif self.v[1] == "%":
                return self.v[0].evaluate() % self.v[2].evaluate()
            elif self.v[1] == "+":
                return self.v[0].evaluate() + self.v[2].evaluate()
            elif self.v[1] == "-":
                return self.v[0].evaluate() - self.v[2].evaluate()
            elif self.v[1] == "<<":
                return self.v[0].evaluate() << self.v[2].evaluate()
            elif self.v[1] == ">>":
                return self.v[0].evaluate() >> self.v[2].evaluate()
            elif self.v[1] == "<":
                return self.v[0].evaluate() < self.v[2].evaluate()
            elif self.v[1] == "<=":
                return self.v[0].evaluate() <= self.v[2].evaluate()
            elif self.v[1] == ">":
                return self.v[0].evaluate() > self.v[2].evaluate()
            elif self.v[1] == ">=":
                return self.v[0].evaluate() >= self.v[2].evaluate()
            elif self.v[1] == "==":
                return self.v[0].evaluate() == self.v[2].evaluate()
            elif self.v[1] == "!=":
                return self.v[0].evaluate() != self.v[2].evaluate()
            elif self.v[1] == "&":
                assert False
            elif self.v[1] == "^":
                assert False
            elif self.v[1] == "|":
                assert False
            elif self.v[1] == "&&":
                assert False
            elif self.v[1] == "||":
                assert False
            else:
                assert False
        else:
            print(len(self.v))
            for i in range(len(self.v)):
                print(i, self.v[i])
            assert False

    def __repr__(self):
        if isinstance(self.v, Expression):
            return repr(self.v)
        else:
            return f"<Expression {self.v}>"

class Literal(Expression):
    def __init__(self, _s, _loc, tokens):
        if isinstance(tokens[0], int):
            self.v = tokens[0]
        elif tokens[0].startswith("#"):
            self.v = int(tokens[0][1:], 2)
        elif tokens[0].startswith("$"):
            self.v = int(tokens[0][1:], 16)
        elif tokens[0].startswith("@"):
            self.v = 0 # TODO
        else:
            assert False

    def evaluate(self, _scope={}):
        return self.v

    def __repr__(self):
        return repr(self.v)

class Variable(Expression):
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 1
        self.name = tokens[0]

    def evaluate(self, scope={}):
        try:
            return scope[self.name]
        except KeyError:
            raise KeyError(f"Variable {self.name} not defined")

    def __repr__(self):
        return f"<{self.name}>"

class Instruction:
    def execute(self, ctl, scope, stack):
        raise NotImplementedError(f"{type(self)} not implemented")

class LabelledInstruction(Instruction):
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 2
        self.label = tokens[0][0] if len(tokens[0]) > 0 else None
        self.instruction = tokens[1]

    def execute(self, ctl, scope, stack):
        return self.instruction.execute(ctl, scope, stack)

class Assignment(Instruction):
    def __init__(self,  _s, _loc, tokens):
        pass

    def execute(self, ctl, scope, stack):
        pass

class BooleanInstruction(Instruction):
    def __init__(self,  _s, _loc, tokens):
        self.decl = tokens[0]
        if len(tokens) == 2:
            self.value = tokens[1]
        else:
            self.value = None

    def execute(self, ctl, scope, stack):
        logger.debug(f"Setting {self.decl.name} to {self.value.evaluate()}...")
        scope[self.decl.name] = self.value.evaluate()

class CallInstruction(Instruction):
    pass

class DrScanInstruction(Instruction):
    pass

class DrStopInstruction(Instruction):
    pass

class ExitInstruction(Instruction):
    pass

class ExportInstruction(Instruction):
    def __init__(self,  _s, _loc, tokens):
        self.key = tokens[0]
        self.data = tokens[1]

    def execute(self, ctl, scope, stack):
        data = self.data.evaluate(scope)
        logger.info(f"EXPORT {self.key}: {data}")
        ctl.export(self.key, data)

class FrequencyInstruction(Instruction):
    pass

class GotoInstruction(Instruction):
    pass

class IfInstruction(Instruction):
    pass

class IntegerInstruction(Instruction):
    def __init__(self,  _s, _loc, tokens):
        self.decl = tokens[0]
        if len(tokens) == 2:
            self.value = tokens[1]
        else:
            self.value = None

    def execute(self, ctl, scope, stack):
        v = self.value.evaluate()
        logger.debug(f"Setting {self.decl.name} to {v}...")
        scope[self.decl.name] = v

class IrScanInstruction(Instruction):
    def __init__(self,  _s, _loc, tokens):
        # print(tokens)
        # assert len(tokens) == 2
        self.length = tokens[0]
        self.value = tokens[1]

    def execute(self, ctl, scope, stack):
        logger.debug(f"Loading {self.value.evaluate(scope)} into IR")

class IrStopInstruction(Instruction):
    pass

class PopInstruction(Instruction):
    pass

class PrintInstruction(Instruction):
    def __init__(self,  _s, _loc, tokens):
        self.parts = tokens

    def execute(self, ctl, scope, stack):
        s = ""
        for part in self.parts:
            if isinstance(part, Expression):
                s += str(part.evaluate(scope))
            else:
                s += str(part)
        print(s)

    def __repr__(self):
        return f"PRINT {', '.join(str(s) for s in self.parts)}"

class PushInstruction(Instruction):
    pass

class StateInstruction(Instruction):
    def __init__(self, _s, _loc, tokens):
        self.states = tokens
        if not self.states[-1].upper() in ("RESET", "IDLE", "DRPAUSE", "IRPAUSE"):
            raise Exception("State must end in one of RESET, IDLE, DRPAUSE, IRPAUSE")

    def execute(self, ctl, scope, stack):
        for state in self.states:
            logger.debug(f"Entering state {state}...")
        logger.warning(f"Instruction not implemented")

class TRSTInstruction(Instruction):
    pass

class WaitInstruction(Instruction):
    pass

class For(Instruction):
    def __init__(self,  _s, _loc, tokens):
        pass

class Procedure:
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 3
        self.enter_label = tokens[0][0][0] if len(tokens[0][0]) > 0 else None
        self.name = tokens[0][1]
        self.statements = tokens[1]
        for statement in self.statements:
            if not isinstance(statement, Instruction):
                print("]]]")
                print(self.name, type(statement), statement)
                print("[[[")
                print()
            # assert isinstance(statement, Instruction)
        self.exit_label = tokens[2][0][0] if len(tokens[2][0]) > 0 else None

    def __repr__(self):
        return f"<Procedure {self.name} ({len(self.statements)} statements)>"

    def execute(self, ctl):
        scope = {}
        stack = []
        for statement in self.statements:
            statement.execute(ctl, scope, stack)

class Data:
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 3
        assert len(tokens[0]) >= 2
        self.name = tokens[0][1]
        self.statements = tokens[1]

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

class StaplFile:
    """STAPL parser"""

    def __init__(self,  tokens):
        self.actions = {}
        self.procedures = {}
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
            elif isinstance(token, Crc):
                if not token.is_correct():
                    logger.warning(f"CRC check failed ({token.actual:04x}, expected: {token.expected:04x})")

    def execute(self, ctl, action):
        try:
            action = self.actions[action]
        except KeyError:
            raise KeyError(f"Action {action} not found")
        for procedure, opt in action.procedures:
            try:
                procedure = self.procedures[procedure]
            except KeyError:
                raise KeyError(f"Procedure {procedure} not found")
            procedure.execute(ctl)

    @classmethod
    def parse(cls, f):
        comments = "`" + pp.SkipTo(pp.LineEnd())
        proc_instruction = pp.Forward()
        expression = pp.Forward()

        identifier = pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]"))
        literal = (pp.MatchFirst((pp.pyparsing_common.integer,
                                  pp.Combine(pp.Literal("#") - pp.OneOrMore(pp.Word(pp.srange("[01]"))), adjacent=False),
                                  pp.Combine(pp.Literal("$") - pp.OneOrMore(pp.Word(pp.srange("[0-9a-fA-F]"))), adjacent=False),
                                  pp.Regex(r"@[^;]*")))).set_parse_action(Literal)
        variable = identifier.copy().set_parse_action(Variable)
        variable_decl = (identifier + pp.Opt(pp.Literal("[").suppress() - expression - pp.Literal("]").suppress())).set_parse_action(VariableDecl)
        function = pp.CaselessKeyword("BOOL") | pp.CaselessKeyword("INT") | pp.CaselessKeyword("CHR$")

        expression0 = (pp.Group(pp.Opt(function) + pp.Literal("(").suppress() + expression + pp.Literal(")").suppress()) | variable | literal).set_parse_action(Expression)
        expression1 = (expression0 + pp.Opt(pp.Literal("[") + pp.Opt(expression + pp.Opt(pp.Literal("..") + expression)) + pp.Literal("]"))).set_parse_action(Expression)
        expression2 = (pp.Opt(pp.one_of("- ! ~")) + expression1).set_parse_action(Expression)
        expression3 = (expression2 + pp.ZeroOrMore(pp.one_of("* / %") + expression2)).set_parse_action(Expression)
        expression4 = (expression3 + pp.ZeroOrMore(pp.one_of("+ -") + expression3)).set_parse_action(Expression)
        expression5 = (expression4 + pp.ZeroOrMore(pp.one_of("<< >>") + expression4)).set_parse_action(Expression)
        expression6 = (expression5 + pp.ZeroOrMore(pp.one_of("<= >= < >") + expression5)).set_parse_action(Expression)
        expression7 = (expression6 + pp.ZeroOrMore(pp.one_of("== !=") + expression6)).set_parse_action(Expression)
        expression8 = (expression7 + pp.ZeroOrMore(pp.Literal("&") + expression7)).set_parse_action(Expression)
        expression9 = (expression8 + pp.ZeroOrMore(pp.Literal("^") + expression8)).set_parse_action(Expression)
        expression10 = (expression9 + pp.ZeroOrMore(pp.Literal("|") + expression9)).set_parse_action(Expression)
        expression11 = (expression10 + pp.ZeroOrMore(pp.Literal("&&") + expression10)).set_parse_action(Expression)
        expression12 = (expression11 + pp.ZeroOrMore(pp.Literal("||") + expression11)).set_parse_action(Expression)
        expression <<= expression12.set_parse_action(Expression)

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
        assignment = (expression + pp.Literal("=") + expression + pp.Suppress(pp.Literal(";"))).set_parse_action(Assignment)
        boolean = (pp.CaselessKeyword("BOOLEAN").suppress() - variable_decl -
                           pp.Opt(pp.Literal("=").suppress() - expression) - pp.Literal(";").suppress()).set_parse_action(BooleanInstruction)
        call = (pp.CaselessKeyword("CALL") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(CallInstruction)
        crc = (pp.CaselessKeyword("CRC").suppress() - pp.Word(pp.srange("[0-9a-fA-F]")) - pp.Literal(";").suppress()).set_parse_action(Crc)
        drscan = (pp.CaselessKeyword("DRSCAN").suppress() - expression - pp.Literal(",").suppress() - expression -
                          pp.Opt(pp.Literal(",").suppress() + pp.CaselessKeyword("CAPTURE") - expression) -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Literal(",").suppress() - expression + pp.Literal(",").suppress() - expression) -
                          pp.Literal(";").suppress()).set_parse_action(DrScanInstruction)
        drstop = (pp.CaselessKeyword("DRSTOP") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(DrStopInstruction)
        exit = (pp.CaselessKeyword("EXIT") - expression - pp.Suppress(pp.Literal(";"))).set_parse_action(ExitInstruction)
        export = (pp.CaselessKeyword("EXPORT").suppress() - pp.QuotedString("\"") - pp.Suppress(pp.Literal(",")) -
                          expression - pp.Literal(";").suppress()).set_parse_action(ExportInstruction)
        for_ = pp.Forward()
        frequency = (pp.CaselessKeyword("FREQUENCY").suppress() - pp.Opt(expression) - pp.Literal(";").suppress()).set_parse_action(FrequencyInstruction)
        goto = (pp.CaselessKeyword("GOTO") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(GotoInstruction)
        if_ = (pp.CaselessKeyword("IF") - expression - pp.CaselessKeyword("THEN") - proc_instruction).set_parse_action(IfInstruction)
        integer = (pp.CaselessKeyword("INTEGER").suppress() - variable_decl -
                           pp.Opt(pp.Literal("=").suppress() - expression - pp.ZeroOrMore(pp.Literal(",").suppress() - expression)) - pp.Literal(";").suppress()).set_parse_action(IntegerInstruction)
        irscan = (pp.CaselessKeyword("IRSCAN").suppress() - expression + pp.Literal(",").suppress() - expression -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("CAPTURE") - expression) -
                          pp.Opt(pp.Literal(",").suppress() - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Literal(",").suppress() - expression - pp.Literal(",").suppress() - expression) -
                          pp.Suppress(pp.Literal(";"))).set_parse_action(IrScanInstruction)
        irstop = (pp.CaselessKeyword("IRSTOP") - identifier - pp.Suppress(pp.Literal(";"))).set_parse_action(IrStopInstruction)
        note = (pp.CaselessKeyword("NOTE").suppress() - pp.QuotedString("\"") - pp.QuotedString("\"") - pp.Literal(";").suppress()).set_parse_action(Note)
        pop = ((pp.CaselessKeyword("POP") - variable - pp.Suppress(pp.Literal(";")))).set_parse_action(PopInstruction)
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
        for_ <<= pp.Group(pp.Group(pp.CaselessKeyword("FOR") - identifier - pp.Literal("=") -
                                   expression - pp.CaselessKeyword("TO") - expression -
                                   pp.Opt(pp.CaselessKeyword("STEP") - expression) - pp.Suppress(pp.Literal(";"))) -
                          pp.ZeroOrMore(proc_statement) -
                          pp.Group(opt_label - pp.CaselessKeyword("NEXT") - identifier - pp.Suppress(pp.Literal(";")))).set_parse_action(For)

        stapl_file = (pp.ZeroOrMore(note) + pp.ZeroOrMore(action) + pp.ZeroOrMore(pp.Or((procedure, data))) +
                      crc + pp.StringEnd())

        stapl_file.ignore(comments)
        stapl_file.enable_packrat()

        return StaplFile(stapl_file.parse_string(f.read()))
