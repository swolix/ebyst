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
import logging

from .data import IntegerVariable, IntegerArrayVariable, BoolVariable, BoolArrayVariable, Evaluatable, Int, Bool, VariableScope
from .stapl import (AssignmentInstruction, BooleanInstruction, CallInstruction, DataInstruction, EndDataInstruction,
                    EndProcedureInstruction, ExitInstruction, ExportInstruction, ForInstruction, GotoInstruction,
                    IfInstruction, IntegerInstruction, NextInstruction, PrintInstruction, ProcedureInstruction)

logger = logging.getLogger(__name__)

class StaplExitCode(Exception):
    def __init__(self, code=0):
        self.code = code

class StaplInterpreter:
    def __init__(self, ctl, stapl):
        self.stapl = stapl
        self.ctl = ctl
        self.call_stack = []
        self.data_scopes = {}
        self.loop_stack = None
        self.scope = None
        self.pc = None

    def execute(self, instruction=None):
        assert not self.scope is None
        assert not self.pc is None
        assert not self.loop_stack is None
        if instruction is None:
            assert self.pc < len(self.stapl.statements)
            instruction = self.stapl.statements[self.pc].instruction
            self.pc += 1

        if isinstance(instruction, AssignmentInstruction):
            v = instruction.value.evaluate(self.scope)
            if not instruction.last is None:
                assert not instruction.first is None
                first = instruction.first.evaluate()
                last = instruction.last.evaluate()
                length = last - first + 1 if last > first else first - last + 1
                if last - first + 1 != len(v):
                    raise ValueError(f"Can't assign slice of length {len(v)} to slice of length {length}")
                logger.debug(f"Setting {instruction.variable}[{first}] to {v}...")
                self.scope[instruction.variable].assign(first, v)
            elif not instruction.first is None:
                first = instruction.first.evaluate()
                logger.debug(f"Setting {instruction.variable}[{first}] to {v}...")
                self.scope[instruction.variable].assign(first, v)
            else:
                logger.debug(f"Setting {instruction.variable} to {v}...")
                self.scope[instruction.variable].assign(v)
        elif isinstance(instruction, BooleanInstruction):
            if instruction.length is None:
                self.scope[instruction.name] = var = BoolVariable()

                if not instruction.value is None:
                    v2 = instruction.value.evaluate(self.scope)
                    logger.debug(f"Setting {instruction.name} to {v2}...")
                    var.assign(v2)
            else:
                self.scope[instruction.name] = var = BoolArrayVariable(instruction.length)

                if not instruction.value is None:
                    for i in range(instruction.length):
                        v = instruction.value[i].evaluate(self.scope)
                        logger.debug(f"Setting {instruction.name}[{i}] to {v}...")
                        var[i].assign(v)
        elif isinstance(instruction, CallInstruction):
            self.call_stack.append((self.pc, self.scope, self.loop_stack))
            self.pc = self.stapl.procedures[instruction.procedure]
            self.scope = VariableScope()
            self.loop_stack = []
        elif isinstance(instruction, DataInstruction):
            pass
        elif isinstance(instruction, EndDataInstruction):
            return False
        elif isinstance(instruction, EndProcedureInstruction):
            if len(self.call_stack) > 0:
                self.pc, self.scope, self.loop_stack = self.call_stack.pop()
            else:
                return False
        elif isinstance(instruction, ExitInstruction):
            raise StaplExitCode(instruction.exit_code.evaluate(self.scope))
        elif isinstance(instruction, ExportInstruction):
            s = ""
            for part in instruction.parts:
                if isinstance(part, Evaluatable):
                    s += str(part.evaluate(self.scope))
                else:
                    s += str(part)
            logger.info(f"EXPORT {instruction.key}: {s}")
            self.ctl.export(instruction.key, s)
        elif isinstance(instruction, ForInstruction):
            start = instruction.start.evaluate(self.scope)
            step = instruction.step.evaluate(self.scope)
            end = instruction.end.evaluate(self.scope)
            self.loop_stack.append((instruction.var, step, end, self.pc))
            self.scope[instruction.var] = var = IntegerVariable()
            var.assign(start)
        elif isinstance(instruction, IfInstruction):
            v = instruction.condition.evaluate(self.scope)
            if Bool(v):
                self.execute(instruction.instruction)
        elif isinstance(instruction, IntegerInstruction):
            if instruction.length is None:
                self.scope[instruction.name] = var = IntegerVariable()

                if not instruction.value is None:
                    v2 = instruction.value.evaluate(self.scope)
                    logger.debug(f"Setting {instruction.name} to {v2}...")
                    var.assign(v2)
            else:
                self.scope[instruction.name] = var = IntegerArrayVariable(instruction.length)

                if not instruction.value is None:
                    for i in range(instruction.length):
                        v = instruction.value[i].evaluate(self.scope)
                        logger.debug(f"Setting {instruction.name}[{i}] to {v}...")
                        var[i].assign(v)
        elif isinstance(instruction, NextInstruction):
            if len(self.loop_stack) == 0:
                raise Exception("NEXT without FOR")
            var, step, end, first_pc = self.loop_stack[-1]
            print(f"CHECK {var} {self.scope[var]} {step} {end}")
            if instruction.var != var:
                raise Exception(f"NEXT variable {instruction.var} doesn't match FOR variable {var}")
            var = self.scope[var]
            var += step
            if (Int(step) > 0 and var < end) or (Int(step) < 0 and var > end):
                self.pc = first_pc
        elif isinstance(instruction, PrintInstruction):
            s = ""
            for part in instruction.parts:
                if isinstance(part, Evaluatable):
                    s += str(part.evaluate(self.scope))
                else:
                    s += str(part)
            print(s)

        elif isinstance(instruction, ProcedureInstruction):
            assert len(self.scope) == 0
            for dep in instruction.uses:
                proc = self.stapl.procedures.get(dep)
                data = self.data_scopes.get(dep)
                if (proc is None) and (data is None):
                    raise Exception("Dependency {dep} not found for procedure {instruction.name}")
                elif not ((proc is None) or (data is None)):
                    raise Exception("Dependency {dep} is ambiguous for procedure {instruction.name}")
                if not data is None:
                    self.scope.update(data)
        else:
            raise NotImplementedError(f"{instruction} not implemented")

        return True

    def _run_procedure(self, pc):
        self.pc = pc
        self.scope = VariableScope()
        self.loop_stack = []
        done = False
        while not done:
            done = not self.execute()

    def run(self, action):
        for name, pc in self.stapl.data_blocks.items():
            logger.info(f"Initializing {name}...")
            self._run_procedure(pc)
            self.data_scopes[name] = self.scope
            self.scope = None
            logger.info(f"Data {name} initialized")

        logger.info(f"Running action {action}...")
        try:
            action = self.stapl.actions[action]
        except KeyError:
            raise KeyError(f"Action {action} not found")
        for procedure, opt in action.procedures:
            try:
                self._run_procedure(self.stapl.procedures[procedure])
            except KeyError:
                raise KeyError(f"Procedure {procedure} not found")
        logger.info(f"Action completed")

