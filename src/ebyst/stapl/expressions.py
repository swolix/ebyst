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

class Evaluatable:
    def evaluate(self, scope={}):
        raise NotImplementedError()

    def as_int(self):
        raise NotImplementedError()

    def as_bool(self):
        raise NotImplementedError()

    def is_int(self):
        return False

    def is_bool(self):
        return False

class Literal(Evaluatable):
    def __init__(self, _s, _loc, tokens):
        if isinstance(tokens[0], int):
            self.v = int(tokens[0])
        elif tokens[0].startswith("#"):
            self.v = int(tokens[0][1:], 2)
        elif tokens[0].startswith("$"):
            self.v = int(tokens[0][1:], 16)
        elif tokens[0].startswith("@"):
            self.v = 0 # TODO
        else:
            assert False

    def evaluate(self, scope={}):
        if self.v == 0 or self.v == 1:
            return Any(self.v)
        else:
            return Int(self.v)

    def __repr__(self):
        return repr(self.v)

class Variable(Evaluatable):
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 1
        self.name = tokens[0]

    def evaluate(self, scope={}):
        try:
            return scope[self.name].evaluate(scope)
        except KeyError:
            raise KeyError(f"Variable {self.name} not defined")

class Any(Evaluatable):
    """Bool or integer"""
    def __init__(self, v):
        self.v = int(v) if not v is None else None

    def evaluate(self, scope):
        return self

    def as_int(self):
        return Int(self.v)

    def as_bool(self):
        return Bool(self.v)

    def __str__(self):
        return str(self.v)

    def __iadd__(self, other):
        if not isinstance(other, Any): raise ValueError()
        self.v += other.v
        return self

    def __imul__(self, other):
        if not isinstance(other, Any): raise ValueError()
        self.v *= other.v
        return self

    def __ifloordiv__(self, other):
        if not isinstance(other, Any): raise ValueError()
        self.v //= other.v
        return self

    def __imod__(self, other):
        if not isinstance(other, Any): raise ValueError()
        self.v %= other.v
        return self

    # def __ior__(self, other):
        # assert False

    def __int__(self):
        return self.v

class Int(Any):
    def evaluate(self, scope):
        return self

    def as_bool(self):
        raise Exception("Can't convert int to bool")

    def is_int(self):
        return True

    def __ge__(self, other):
        if not isinstance(other, Any): raise ValueError()
        return self.v >= other.v

    def __gt__(self, other):
        if not isinstance(other, Any): raise ValueError()
        return self.v > other.v

    def __le__(self, other):
        if not isinstance(other, Any): raise ValueError()
        return self.v <= other.v

    def __lt__(self, other):
        if not isinstance(other, Any): raise ValueError()
        return self.v < other.v

    def __eq__(self, other):
        if not isinstance(other, Any): raise ValueError()
        return self.v == other.v

    def __ne__(self, other):
        if not isinstance(other, Any): raise ValueError()
        return self.v != other.v

    def __invert__(self):
        self.v = ~self.v
        return self

class Bool(Any):
    def __init__(self, v):
        if v is None:
            self.v = None
        elif int(v) == 0 or int(v) == 1:
            self.v = int(v)
        else:
            raise ValueError(f"Boolean value must be 0 or 1, not {v}")

    def evaluate(self, scope):
        return self

    def as_int(self):
        raise Exception("Can't convert bool to int")

    def is_bool(self):
        return True

    def __invert__(self):
        self.v = 0 if self.v else 1
        return self

class String(Evaluatable):
    def __init__(self, v):
        self.v = str(v)

    def __str__(self):
        return self.v

class Function(Evaluatable):
    def __init__(self,  _s, _loc, tokens):
        assert len(tokens) == 1
        assert len(tokens[0]) == 2
        self.function = tokens[0][0]
        self.v = tokens[0][1]

    def evaluate(self, scope={}):
        if self.function == "BOOL":
            return Bool(int(self.v.evaluate(scope)))
        elif self.function == "INT":
            return Int(int(self.v.evaluate(scope)))
        elif self.function == "CHR$":
            return String(chr(int(self.v.evaluate(scope))))
        else:
            assert False

    def __str__(self):
        return f"{self.function}({self.v})"

class Expression(Evaluatable):
    def __init__(self,  _s, _loc, tokens):
        self.v = tokens

    def evaluate(self, scope={}):
        if len(self.v) == 1:
            return self.v[0].evaluate(scope)
        elif len(self.v) == 2:
            if self.v[0] == "~":
                return ~Int(self.v[1].evaluate(scope))
            elif self.v[0] == "!":
                return ~Bool(self.v[1].evaluate(scope))
            else:
                print(self)
                assert False
        elif len(self.v) >= 3 and (len(self.v) & 1) == 1:
            r = self.v[0].evaluate(scope)
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
                    r = Bool(r <= b)
                elif self.v[i] == "<":
                    r = Bool(r < b)
                elif self.v[i] == ">=":
                    r = Bool(r >= b)
                elif self.v[i] == ">":
                    r = Bool(r > b)
                elif self.v[i] == "==":
                    r = Bool(r == b)
                elif self.v[i] == "!=":
                    r = Bool(r != b)
                elif self.v[i] == "&&":
                    r = Bool(int(r) and int(b))
                elif self.v[i] == "||":
                    r = Bool(int(r) or int(b))
                else:
                    print(self)
                    assert False
            assert isinstance(r, Any)
            return r
        else:
            print(self)
            assert False

    def __repr__(self):
        return "(" + "".join([str(v) for v in self.v]) + ")"

    @classmethod
    def get_parse_rule(cls):
        expression = pp.Forward()
        variable = pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]")).set_parse_action(Variable)
        literal = (pp.MatchFirst((pp.pyparsing_common.integer,
                                  pp.Combine(pp.Literal("#") - pp.OneOrMore(pp.Word(pp.srange("[01]"))), adjacent=False),
                                  pp.Combine(pp.Literal("$") - pp.OneOrMore(pp.Word(pp.srange("[0-9a-fA-F]"))), adjacent=False),
                                  pp.Regex(r"@[^;]*")))).set_parse_action(Literal)
        function = (pp.Group(pp.CaselessKeyword("BOOL") | pp.CaselessKeyword("INT") | pp.CaselessKeyword("CHR$") + 
                             pp.Literal("(").suppress() + expression + pp.Literal(")").suppress())).set_parse_action(Function)

        expression0 = (function | variable | literal).set_parse_action(cls)
        expression1 = (expression0 + pp.Opt(pp.Literal("[") + pp.Opt(expression + pp.Opt(pp.Literal("..") + expression)) + pp.Literal("]"))).set_parse_action(cls)
        expression2 = (pp.Opt(pp.one_of("- ! ~")) + expression1).set_parse_action(cls)
        expression3 = (expression2 + pp.ZeroOrMore(pp.one_of("* / %") + expression2)).set_parse_action(cls)
        expression4 = (expression3 + pp.ZeroOrMore(pp.one_of("+ -") + expression3)).set_parse_action(cls)
        expression5 = (expression4 + pp.ZeroOrMore(pp.one_of("<< >>") + expression4)).set_parse_action(cls)
        expression6 = (expression5 + pp.ZeroOrMore(pp.one_of("<= >= < >") + expression5)).set_parse_action(cls)
        expression7 = (expression6 + pp.ZeroOrMore(pp.one_of("== !=") + expression6)).set_parse_action(cls)
        expression8 = (expression7 + pp.ZeroOrMore(pp.Literal("&") + expression7)).set_parse_action(cls)
        expression9 = (expression8 + pp.ZeroOrMore(pp.Literal("^") + expression8)).set_parse_action(cls)
        expression10 = (expression9 + pp.ZeroOrMore(pp.Literal("|") + expression9)).set_parse_action(cls)
        expression11 = (expression10 + pp.ZeroOrMore(pp.Literal("&&") + expression10)).set_parse_action(cls)
        expression12 = (expression11 + pp.ZeroOrMore(pp.Literal("||") + expression11)).set_parse_action(cls)
        expression <<= expression12.set_parse_action(cls)
        return expression
