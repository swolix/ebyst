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

logger = logging.getLogger(__name__)

class BSDLReader:
    """Poor mans BSDL parser"""
    class Token:
        pass
    
    class Whitespace(Token):
        RE = re.compile("[ \t\r\n]+")

    class Comments(Token):
        RE = re.compile("--[^\r\n]*")

    class Identifier(Token):
        RE = re.compile("[A-Za-z_][A-Za-z_0-9\\.]*")

    class Symbol(Token):
        RE = re.compile("[\\(\\):=;&,]")

    class String(Token):
        RE = re.compile("\"[^\"]*\"")

    class Number(Token):
        RE = re.compile("[0-9]+(\\.[0-9]+)?(e[0-9]+)?")

    TOKENS = [Whitespace, Comments, Identifier, Symbol, String, Number]

    def __init__(self, data):
        self.data = data
        self.offset = 0

    def tokens(self):
        while self.offset < len(self.data):
            m = None
            for token in BSDLReader.TOKENS:
                m = token.RE.match(self.data[self.offset:])
                if m:
                    self.offset += m.end()
                    break
            if m:
                if not token in (BSDLReader.Whitespace, BSDLReader.Comments):
                    yield token, m.group(0)
            else:
                raise Exception(f"Parse error @ {self.offset}")

    def combine_strings(self):
        it = self.tokens()
        while True:
            try:
                token, str = next(it)
                if token == BSDLReader.String:
                    while True:
                        token2, str2 = next(it)
                        if token2 == BSDLReader.Symbol and str2 == "&":
                            token3, str3 = next(it)
                            if token3 == BSDLReader.String:
                                str = str[:-1] + str3[1:]
                            else:
                                raise Exception("Invalid format")
                        else:
                            yield token, str
                            yield token2, str2
                            break
                else:
                    yield token, str
            except StopIteration:
                break
            
    def attributes(self):
        it = self.combine_strings()
        while True:
            try:
                token, str = next(it)
                if token == BSDLReader.Identifier and str.lower() == "attribute":
                    token, name = next(it)
                    if token != BSDLReader.Identifier: raise Exception("Invalid format")
                    token, str = next(it)
                    if token != BSDLReader.Identifier: raise Exception("Invalid format")
                    if str.lower() != "of": raise Exception("Invalid format")
                    token, object_ = next(it)
                    if token != BSDLReader.Identifier: raise Exception("Invalid format")
                    token, str = next(it)
                    if token != BSDLReader.Symbol: raise Exception("Invalid format")
                    if str.lower() != ":": raise Exception("Invalid format")
                    token, type_ = next(it)
                    if token != BSDLReader.Identifier: raise Exception("Invalid format")
                    token, str = next(it)
                    if token != BSDLReader.Identifier: raise Exception("Invalid format")
                    if str.lower() != "is": raise Exception("Invalid format")
                    token, value = next(it)
                    yield name, object_, type_, value
            except StopIteration:
                break

    @classmethod
    def parse(cls, f):
        attributes = {}
        reader = cls(f.read())
        for name, object_, type_, value in reader.attributes():
            attributes[name.upper()] = value

        return attributes
