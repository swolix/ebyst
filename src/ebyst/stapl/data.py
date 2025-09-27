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

class Variable:
    pass

class VariableScope(dict):
    def __setitem__(self, key: str, value: Variable) -> None:
        assert isinstance(value, Variable)
        return super().__setitem__(key, value)

class Evaluatable:
    def evaluate(self, scope=VariableScope()):
        raise NotImplementedError()

class Literal(Evaluatable):
    def __init__(self, s):
        if isinstance(s, int):
            self.v = int(s)
        elif s.startswith("#"):
            self.v = int(s[1:], 2)
        elif s.startswith("$"):
            self.v = int(s[1:], 16)
        elif s.startswith("@"):
            self.v = 0 # TODO
        else:
            assert False

    def evaluate(self, scope=VariableScope()):
        if self.v == 0 or self.v == 1:
            return Any(self.v)
        else:
            return Int(self.v)

    def __str__(self):
        return str(self.v)

class Int(Evaluatable):
    def __init__(self, v):
        if (isinstance(v, int) or isinstance(v, str)) and not isinstance(v, bool):
            self.v = int(v)
        elif isinstance(v, Any) or isinstance(v, Int):
            self.v = v.v
        else:
            raise ValueError(f"Could not convert {repr(v)} to Int")

    def evaluate(self, scope=VariableScope()):
        return self

    def __add__(self, other):
        return Int(self.v + Int(other).v)

    def __sub__(self, other):
        return Int(self.v - Int(other).v)

    def __mul__(self, other):
        return Int(self.v * Int(other).v)

    def __floordiv__(self, other):
        return Int(self.v // Int(other).v)

    def __mod__(self, other):
        return Int(self.v % Int(other).v)

    def __lshift__(self, other):
        return Int(self.v << Int(other).v)

    def __rshift__(self, other):
        return Int(self.v >> Int(other).v)

    def __and__(self, other):
        return Int(self.v & Int(other).v)

    def __or__(self, other):
        return Int(self.v | Int(other).v)

    def __xor__(self, other):
        return Int(self.v ^ Int(other).v)

    def __ge__(self, other):
        return Bool(self.v >= Int(other).v)

    def __gt__(self, other):
        return Bool(self.v > Int(other).v)

    def __le__(self, other):
        return Bool(self.v <= Int(other).v)

    def __lt__(self, other):
        return Bool(self.v < Int(other).v)

    def __eq__(self, other):
        return Bool(self.v == Int(other).v)

    def __ne__(self, other):
        return Bool(self.v != Int(other).v)

    def __invert__(self):
        return Int(~self.v)

    def __neg__(self):
        return Int(-self.v)

    def __str__(self):
        return str(self.v)

    def __int__(self):
        return self.v

    def __repr__(self):
        return f"Int({self.v})"

    def clone(self):
        return Int(self)

class Bool(Evaluatable):
    def __init__(self, v):
        if (isinstance(v, int) or isinstance(v, str)) and int(v) in (0, 1):
            self.v = int(v)
        elif (isinstance(v, Any) or isinstance(v, Bool)) and v.v in (0, 1):
            self.v = v.v
        else:
            raise ValueError(f"Could not convert {repr(v)} to Bool")

    def evaluate(self, scope=VariableScope()):
        return self

    def __eq__(self, other):
        return Bool(self.v == Bool(other).v)

    def __ne__(self, other):
        return Bool(self.v != Bool(other).v)

    def __and__(self, other):
        return Bool(self.v and Bool(other).v)

    def __or__(self, other):
        return Bool(self.v or Bool(other).v)

    def __xor__(self, other):
        return Bool(self.v ^ Bool(other).v)

    def __invert__(self):
        return Bool(0 if self.v else 1)

    def __bool__(self):
        return bool(self.v)

    def __str__(self):
        return str(self.v)

    def __repr__(self):
        return f"Bool({self.v})"

    def clone(self):
        return Bool(self.v)

class Any(Int):
    """Boolean or integer"""
    def __init__(self, v):
        if isinstance(v, int) or isinstance(v, str) or isinstance(v, Any):
            self.v = int(v)
        else:
            raise ValueError(f"Could not convert {repr(v)} to Any")

    def evaluate(self, scope=VariableScope()):
        return self

    def __eq__(self, other):
        if isinstance(other, Bool):
            return Bool(self) == other
        else:
            return Int(self) == other

    def __ne__(self, other):
        if isinstance(other, Bool):
            return Bool(self) != other
        else:
            return Int(self) != other

    def __and__(self, other):
        return NotImplemented

    def __or__(self, other):
        return NotImplemented

    def __xor__(self, other):
        return NotImplemented

    def __str__(self):
        return str(self.v)

    def __repr__(self):
        return f"Any({self.v})"

    def __int__(self):
        return self.v

    def __bool__(self):
        return bool(self.v)

    def clone(self):
        return Any(self)

class String(Evaluatable):
    def __init__(self, v):
        self.v = str(v)

    def __str__(self):
        return self.v

    def __repr__(self):
        return f"String({self.v})"

class IntegerVariable(Int, Variable):
    def __init__(self):
        self.v = None
    
    def assign(self, v):
        Int.__init__(self, v)

    def __iadd__(self, other):
        self.v += Int(other).v
        return self

class IntegerArrayVariable(list, Variable, Evaluatable):
    def __init__(self, length):
        for i in range(length): self.append(IntegerVariable())

class BoolVariable(Evaluatable, Variable):
    def __init__(self):
        self.v = None
    
    def assign(self, v):
        if isinstance(v, Bool):
            self.v = v
        elif isinstance(v, Any):
            self.v = Bool(v)
        else:
            raise ValueError(f"Cannot assign {repr(v)} to Bool")

    def evaluate(self, scope=VariableScope()):
        return self.v

class BoolArrayVariable(list, Variable, Evaluatable):
    def __init__(self, length):
        for i in range(length): self.append(BoolVariable())
