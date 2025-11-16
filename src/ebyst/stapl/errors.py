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
class StaplError(Exception):
    def __init__(self, message, pc=None):
        self.pc = pc
        self.message = message

    def __str__(self):
        if not self.pc is None:
            r = f"{self.pc}: {self.message}"
        else:
            r = self.message
        return r

class VariableNotDefined(StaplError):
    def __init__(self, var):
        StaplError.__init__(self, f"Variable {var} not defined")
        self.var = var

class InvalidState(StaplError):
    def __init__(self, state):
        StaplError.__init__(self, f"Invalid state {state}")
        self.state = state

class LabelNotDefined(StaplError):
    def __init__(self, label):
        StaplError.__init__(self, f"Label {label} not defined")
        self.label = label

class StaplValueError(StaplError):
    pass
