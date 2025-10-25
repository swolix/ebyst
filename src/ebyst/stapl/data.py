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
from bitarray import bitarray

class VariableScope(dict):
    pass

class Evaluatable:
    def evaluate(self, scope=VariableScope()):
        raise NotImplementedError()

class Array:
    pass

class Variable(Evaluatable):
    def __init__(self, v):
        assert isinstance(v, Evaluatable)
        self.v = v

    def assign(self, v):
        if not isinstance(self.v, Any):
            v = type(self.v)(v)
        assert isinstance(v, Evaluatable)
        self.v = v

    def evaluate(self, scope=VariableScope()):
        return self.v.evaluate(scope)

class ArrayVariable(Variable):
    def __init__(self, v):
        assert isinstance(v, Evaluatable)
        len(v)
        self.v = v

    def assign(self, offset_or_v, v=None):
        if v is None:
            offset = 0
            v = offset_or_v
        else:
            offset = int(offset_or_v.evaluate())
        if isinstance(v, Array):
            self.v[offset:offset+len(v)] = v
        else:
            self.v[offset] = v

    def evaluate(self, scope=VariableScope()):
        return self.v.evaluate(scope)

class CheckedVariableScope(VariableScope):
    def __setitem__(self, key: str, value: Variable) -> None:
        assert isinstance(value, Variable)
        return super().__setitem__(key, value)

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
        elif isinstance(v, bitarray) and len(v) == 1:
            self.v = 1 if v[0] else 0
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

class IntArray(list, Evaluatable, Array):
    def __getitem__(self, i):
        if isinstance(i, int):
            return Int(super().__getitem__(i))
        elif isinstance(i, slice):
            assert i.step is None

            if i.start <= i.stop:
                return IntArray(super().__getitem__(slice(i.start, i.stop+1)))
            else:
                return IntArray(super().__getitem__(slice(i.start, i.stop-1 if i.stop > 0 else None, -1)))
        else:
            assert False

    def evaluate(self, scope=VariableScope()):
        return self

class BoolArray(Evaluatable, Array):
    def __init__(self, v):
        self.v = bitarray(v, endian="big")
        if isinstance(v, str):
            self.v.reverse()

    def __getitem__(self, i):
        if isinstance(i, int):
            return Bool(self.v[i])
        elif isinstance(i, slice):
            assert i.step is None

            if i.start <= i.stop:
                return BoolArray(self.v.__getitem__(slice(i.start, i.stop+1)))
            else:
                x = self.v.__getitem__(slice(i.stop, i.start+1))
                x.reverse()
                return BoolArray(x)
        else:
            assert False


    def __setitem__(self, i, v):
        self.v[i] = v.v

    def __len__(self):
        return len(self.v)

    def __str__(self):
        return self.v.to01()

    def __repr__(self):
        return repr(self.v)

    def evaluate(self, scope=VariableScope()):
        return self

class String(Evaluatable):
    def __init__(self, v):
        self.v = str(v)

    def __str__(self):
        return self.v

    def __repr__(self):
        return f"String({self.v})"
