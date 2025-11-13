#!/usr/bin/env python3
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
import math
from bitarray.util import ba2int, hex2ba
from bitarray import bitarray
from binascii import hexlify

def _get_6bits(compressed: str):
    for c in compressed:
        c = ord(c)
        if c >= 0x30 and c <= 0x39:
            yield c - 0x30
        elif c >= 0x41 and c <= 0x5a:
            yield c - 0x41 + 10
        elif c >= 0x61 and c <= 0x7a:
            yield c - 0x61 + 36
        elif c == 0x5f:
            yield 0x3e
        elif c == 0x40:
            yield 0x3f
        elif c in (0x08, 0x0a, 0x0d, 0x20):
            pass
        else:
            raise ValueError(f"Invalid character in compressed stream (0x{c:02x})")

def _get_bytes(compressed: str):
    it = _get_6bits(compressed)
    try:
        while True:
            a = next(it)
            b = next(it)
            yield a | ((b & 0x03) << 6)
            c = next(it)
            yield ((b & 0x3c) >> 2) | ((c & 0x0f) << 4)
            d = next(it)
            yield ((c & 0x30) >> 4) | (d << 2)
    except StopIteration:
        pass

def decompress(compressed: str):
    ba = bitarray(endian='little', buffer=bytes(_get_bytes(compressed)))
    length = ba2int(ba[:32])
    ret = bytearray(length)
    ioffset = 32
    ooffset = 0
    while ooffset < length:
        if ba[ioffset] == 0:
            ioffset += 1
            for _ in range(3):
                ret[ooffset:ooffset+1] = bytes([ba2int(ba[ioffset:ioffset+8])])
                ioffset += 8
                ooffset += 1
        else:
            ioffset += 1
            bits = min(math.ceil(math.log2(ooffset)), 13)
            repeat_offset = ba2int(ba[ioffset:ioffset+bits])
            ioffset += bits
            repeat_length = ba2int(ba[ioffset:ioffset+8])
            ioffset += 8
            ret[ooffset:ooffset+repeat_length] = ret[ooffset-repeat_offset:ooffset-repeat_offset+repeat_length]
            ooffset += repeat_length

    return ret

if __name__ == "__main__":
    assert decompress("O00008Cn63PbPMRWpGBDgj6RV60") == b"abcdefabcdefghijkldefabc"

    v = bitarray("101101111", endian='little')
    v.reverse()
    print(f"BIN: {v}")

    v = bitarray(hex2ba("16F", endian='big'), 'little')
    v.reverse()
    print(f"HEX: {v}")

    x = decompress("30000uj000")
    v = bitarray(endian='little')
    v.frombytes(x)
    print(f"ACA: {v}")
