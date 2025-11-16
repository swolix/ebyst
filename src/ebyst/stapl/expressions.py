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
import pyparsing as pp
import re
from .data import Evaluatable, Int, Bool, BoolArray, Any, String, VariableScope
from . import aca, errors # type: ignore
from bitarray import bitarray
from bitarray.util import hex2ba, int2ba, ba2int

class VariableRef(Evaluatable):
    def __init__(self,  _s, _loc, tokens):
        if len(tokens) == 1:
            self.name = tokens[0]
            self.slice_start = None
            self.slice_end = None
        elif len(tokens) == 2:
            self.name = tokens[0]
            self.slice_start = tokens[1]
            self.slice_end = None
        elif len(tokens) == 3:
            self.name = tokens[0]
            self.slice_start = tokens[1]
            self.slice_end = tokens[2]
        else:
            print(tokens)
            assert False

    def evaluate(self, scope=VariableScope()):
        variable = scope[self.name]
        if not self.slice_end is None:
            assert not self.slice_start is None
            return variable.evaluate(scope)[slice(int(self.slice_start.evaluate(scope)), int(self.slice_end.evaluate(scope)))]
        elif not self.slice_start is None:
            return variable.evaluate(scope)[int(self.slice_start.evaluate(scope))].evaluate(scope)
        else:
            return variable.evaluate(scope)

    def __str__(self):
        if not self.slice_end is None:
            return f"{self.name}[{self.slice_start}..{self.slice_end}]"
        elif not self.slice_start is None:
            return f"{self.name}[{self.slice_start}]"
        else:
            return self.name

class BoolArrayParser(Evaluatable):
    def __init__(self, _s, _loc, tokens):
        assert len(tokens) == 1
        self.s = tokens[0]
        assert self.s[0] in "#@$"
        self.ba = None

    def evaluate(self, scope=VariableScope()):
        if self.ba is None:
            if self.s[0] == '#':
                self.ba = bitarray(re.sub(r'\s+', '', self.s[1:]), endian='little')
                self.ba.reverse()
            elif self.s[0] == '$':
                self.ba = bitarray(hex2ba(re.sub(r'\s+', '', self.s[1:]), endian='big'), 'little')
                self.ba.reverse()
            elif self.s[0] == '@':
                self.ba = bitarray(endian='little')
                self.ba.frombytes(aca.decompress(self.s[1:]))
            else:
                assert False

        return BoolArray(self.ba)

    def __str__(self):
        return self.s

class IntParser(Evaluatable):
    def __init__(self, _s, _loc, tokens):
        assert len(tokens) == 1
        self.v = int(tokens[0])

    def evaluate(self, scope=VariableScope()):
        if self.v == 0 or self.v == 1:
            return Any(self.v)
        else:
            return Int(self.v)

    def __str__(self):
        return str(self.v)

class Function(Evaluatable):
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 1
        assert len(tokens[0]) == 2
        self.function = tokens[0][0]
        self.v = tokens[0][1]

    def evaluate(self, scope={}):
        if self.function == "BOOL":
            ba = int2ba(int(self.v.evaluate(scope)), length=32, signed=True, endian='little')
            return BoolArray(ba)
        elif self.function == "INT":
            ba = self.v.evaluate(scope).v
            if len(ba) < 32:
                ba = ba + bitarray(32 - len(ba), endian='little')
            if len(ba) > 32:
                ba = ba[:32]
            return Int(ba2int(ba, signed=True))
        elif self.function == "CHR$":
            return String(chr(Int(self.v.evaluate(scope)).v))
        else:
            assert False

    def __str__(self):
        return f"{self.function}({self.v})"

class Expression(Evaluatable):
    def __init__(self,  _s, _loc, tokens):
        self.v = list(tokens)

    def optimize(self):
        try:
            return self.evaluate()
        except errors.VariableNotDefined:
            if len(self.v) == 1:
                return self.v[0].optimize()
            else:
                for i in range(len(self.v)):
                    try:
                        self.v[i] = self.v[i].optimize()
                    except AttributeError:
                        pass
                return self

    def evaluate(self, scope=VariableScope()):
        if len(self.v) == 1:
            return self.v[0].evaluate(scope)
        elif len(self.v) == 2:
            if self.v[0] == "~":
                return ~Int(self.v[1].evaluate(scope))
            elif self.v[0] == "-":
                return -Int(self.v[1].evaluate(scope))
            elif self.v[0] == "!":
                return ~Bool(self.v[1].evaluate(scope))
            else:
                print(self)
                assert False
        elif len(self.v) >= 3 and (len(self.v) & 1) == 1:
            r = self.v[0].evaluate(scope).clone()
            for i in range(1, len(self.v), 2):
                b = self.v[i+1].evaluate(scope)
                if self.v[i] == "*":
                    r *= b
                elif self.v[i] == "/":
                    r //= b
                elif self.v[i] == "%":
                    r %= b
                elif self.v[i] == "+":
                    r += b
                elif self.v[i] == "-":
                    r -= b
                elif self.v[i] == "<<":
                    r <<= b
                elif self.v[i] == ">>":
                    r >>= b
                elif self.v[i] == "&":
                    r &= b
                elif self.v[i] == "^":
                    r ^= b
                elif self.v[i] == "|":
                    r |= b
                elif self.v[i] == "<=":
                    r = r <= b
                elif self.v[i] == "<":
                    r = r < b
                elif self.v[i] == ">=":
                    r = r >= b
                elif self.v[i] == ">":
                    r = r > b
                elif self.v[i] == "==":
                    r = r == b
                elif self.v[i] == "!=":
                    r = r != b
                elif self.v[i] == "&&":
                    r = Bool(r)
                    r &= b
                elif self.v[i] == "||":
                    r = Bool(r)
                    r |= b
                else:
                    print(self)
                    assert False
            assert isinstance(r, Bool) or isinstance(r, Int) or isinstance(r, Any)
            return r
        else:
            print(self.v)
            assert False

    def __str__(self):
        return "(" + "".join([str(v) for v in self.v]) + ")"

    @classmethod
    def get_parse_rule(cls):
        expression = pp.Forward()
        variable = (pp.Regex(r"[a-zA-Z][a-zA-Z0-9_]*") +
                    pp.Opt(pp.Literal("[").suppress() + pp.Opt(expression + pp.Opt(pp.Literal("..").suppress() + expression)) +
                           pp.Literal("]").suppress())).set_parse_action(VariableRef)
        literal = pp.pyparsing_common.integer.set_parse_action(IntParser) | (pp.MatchFirst((
                                  pp.Regex(r"#[01\s]+"),
                                  pp.Regex(r"\$[0-9a-fA-F\s]+"),
                                  pp.Regex(r"@[^;]+")))).set_parse_action(BoolArrayParser)
        function = (pp.Group((pp.CaselessKeyword("BOOL") | pp.CaselessKeyword("INT") | pp.CaselessKeyword("CHR$")) +
                             pp.Literal("(").suppress() + expression + pp.Literal(")").suppress())).set_parse_action(Function)

        expression0 = (function | variable | literal).set_parse_action(cls)
        expression1 = expression0 | (pp.Literal("(").suppress() - expression - pp.Literal(")").suppress())
        expression2 = (pp.Opt(pp.one_of("- ! ~")) + expression1).set_parse_action(cls)
        expression3 = (expression2 - pp.ZeroOrMore(pp.one_of("* / %") + expression2)).set_parse_action(cls)
        expression4 = (expression3 - pp.ZeroOrMore(pp.one_of("+ -") + expression3)).set_parse_action(cls)
        expression5 = (expression4 - pp.ZeroOrMore(pp.one_of("<< >>") + expression4)).set_parse_action(cls)
        expression6 = (expression5 - pp.ZeroOrMore(pp.one_of("<= >= < >") + expression5)).set_parse_action(cls)
        expression7 = (expression6 - pp.ZeroOrMore(pp.one_of("== !=") + expression6)).set_parse_action(cls)
        expression8 = (expression7 - pp.ZeroOrMore(pp.Literal("&") + expression7)).set_parse_action(cls)
        expression9 = (expression8 - pp.ZeroOrMore(pp.Literal("^") + expression8)).set_parse_action(cls)
        expression10 = (expression9 - pp.ZeroOrMore(pp.Literal("|") + expression9)).set_parse_action(cls)
        expression11 = (expression10 - pp.ZeroOrMore(pp.Literal("&&") + expression10)).set_parse_action(cls)
        expression12 = (expression11 - pp.ZeroOrMore(pp.Literal("||") + expression11)).set_parse_action(cls)
        expression <<= expression12.set_parse_action(cls, lambda _s, _loc, tokens: tokens[0].optimize()) # type: ignore
        return expression
