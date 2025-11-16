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
from binascii import hexlify
from bitarray import bitarray

from . import errors

class VariableScope(dict):
    def __getitem__(self, key: str):
        try:
            return super().__getitem__(key)
        except KeyError:
            raise errors.VariableNotDefined(key) from None

class Evaluatable:
    def evaluate(self, scope=VariableScope()):
        raise NotImplementedError()

    def optimize(self):
        return self

class Array(Evaluatable):
    def __getitem__(self, k):
        raise NotImplementedError()

    def __setitem__(self, k, v):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

class Variable(Evaluatable):
    def __init__(self, v):
        assert isinstance(v, Evaluatable)
        self.v = v

    def assign(self, v, *args, **kwargs):
        if not isinstance(self.v, Any):
            v = type(self.v)(v) # type: ignore
        assert isinstance(v, Evaluatable)
        self.v = v

    def evaluate(self, scope=VariableScope()):
        return self.v.evaluate(scope)

class ArrayVariable(Variable, Array):
    def __init__(self, v):
        assert isinstance(v, Array)
        len(v)
        self.v = v

    def assign(self, pos_or_v, v=None):
        if v is None:
            slice_ = None
            v = pos_or_v
        elif isinstance(pos_or_v, int) or isinstance(pos_or_v, slice):
            slice_ = pos_or_v
        else:
            assert False

        self.v.__setitem__(slice_, v)

    def evaluate(self, scope=VariableScope()):
        return self.v.evaluate(scope)

    def __len__(self):
        return len(self.v)

    def __str__(self):
        return str(self.v)

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
            raise errors.StaplValueError(f"Could not convert {repr(v)} to Int")

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

    def __eq__(self, other): # type: ignore
        return Bool(self.v == Int(other).v)

    def __ne__(self, other): # type: ignore
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
            raise errors.StaplValueError(f"Could not convert {repr(v)} to Bool")

    def evaluate(self, scope=VariableScope()):
        return self

    def __eq__(self, other): # type: ignore
        return Bool(self.v == Bool(other).v)

    def __ne__(self, other): # type: ignore
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
            raise errors.StaplValueError(f"Could not convert {repr(v)} to Any")

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

class IntArray(list, Array):
    def __init__(self, init=[]):
        for x in init:
            if isinstance(x, int):
                self.append(Int(x))
            elif isinstance(x, Int):
                self.append(x)
            else:
                raise errors.StaplValueError(f"Can't convert {x} to Int")

    def __getitem__(self, i): # type: ignore
        if isinstance(i, int):
            return Int(super().__getitem__(i))
        elif isinstance(i, slice):
            assert i.step is None

            if i.start <= i.stop:
                return IntArray(super().__getitem__(slice(i.start, i.stop+1)))
            else:
                return IntArray(super().__getitem__(slice(i.start, i.stop-1 if i.stop > 0 else None, -1)))
        else:
            raise TypeError(f"Invalid type {type(i)} for slice")

    def __setitem__(self, i, v):
        if i is None:
            if not isinstance(v, IntArray):
                raise errors.StaplValueError(f"Can't assign {type(v)} to integer array")
            super().__setitem__(slice(0, len(self)), v)
        elif isinstance(i, int):
            if not isinstance(v, Int):
                raise errors.StaplValueError(f"Can't assign {v} to integer array element")
            super().__setitem__(i, v)
        elif isinstance(i, slice):
            assert i.step is None
            if not isinstance(v, IntArray):
                TypeError(f"Can't assign {type(v)} to integer array")

            try:
                if i.start <= i.stop:
                    super().__setitem__(slice(i.start, i.stop+1), v)
                else:
                    super().__setitem__(slice(i.start, i.stop-1 if i.stop > 0 else None, -1), v)
            except (TypeError, ValueError) as e:
                raise errors.StaplValueError(str(e)) from None
        else:
            raise TypeError(f"Invalid type {type(i)} for slice")

    def evaluate(self, scope=VariableScope()):
        return self

class BoolArray(Array):
    def __init__(self, v):
        self.v = bitarray(v, endian='little')
        if isinstance(v, str):
            self.v.reverse()

    def __getitem__(self, i):
        if isinstance(i, int):
            return Bool(self.v[i])
        elif isinstance(i, slice):
            assert i.step is None

            if i.start < i.stop:
                x = self.v.__getitem__(slice(i.stop, i.start-1 if i.start > 0 else None, -1))
                return BoolArray(x)
            else:
                x = self.v.__getitem__(slice(i.stop, i.start+1))
                return BoolArray(x)
        else:
            raise TypeError(f"Invalid type {type(i)} for slice")

    def __setitem__(self, i, v):
        if i is None:
            self.v.setall(0)
            self.__setitem__(slice(min(len(v), len(self))-1, 0), v)
        elif isinstance(i, int):
            if isinstance(v, Bool) or isinstance(v, Any):
                self.v.__setitem__(i, v.v)
            else:
                raise errors.StaplValueError(f"Can't assign {v} to boolean array element")
        elif isinstance(i, slice):
            assert i.step is None
            if not isinstance(v, BoolArray):
                raise errors.StaplValueError(f"Can't assign {type(v)} to boolean array")

            slice_length = i.stop - i.start + 1 if i.stop > i.start else i.start - i.stop + 1
            if len(v) > slice_length:
                v = BoolArray(v.v[:slice_length])
            elif len(v) < slice_length:
                v = BoolArray(v.v + bitarray("0", endian='little') * (slice_length - len(v)))

            if i.start < i.stop:
                self.v.__setitem__(slice(i.stop, i.start-1 if i.start > 0 else None, -1), v.v)
            else:
                self.v.__setitem__(slice(i.stop, i.start+1), v.v)
        else:
            raise TypeError(f"Invalid type {type(i)} for slice")

    def __eq__(self, other):
        if not isinstance(other, BoolArray): return False
        return self.v == other.v

    def __len__(self):
        return len(self.v)

    def __str__(self):
        return hexlify(self.v.tobytes()[::-1]).decode("ascii")

    def __repr__(self):
        return repr(self.v)

    def evaluate(self, scope=VariableScope()):
        return self

    def reverse(self):
        x = BoolArray(self.v)
        x.v.reverse()
        return x

    def to_bitarray(self):
        return self.v

    def extend(self, length):
        while len(self.v) < length: self.v.append(0)

    def __and__(self, other):
        return self.v & other.v

class String:
    def __init__(self, v):
        self.v = str(v)

    def __str__(self):
        return self.v

    def __repr__(self):
        return f"String({self.v})"
