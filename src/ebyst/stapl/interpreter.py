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

from ..tap_controller import State
from .data import Variable, Evaluatable, Int, IntArray, Bool, BoolArray, CheckedVariableScope, ArrayVariable
from .stapl import (AssignmentInstruction, BooleanInstruction, CallInstruction, DataInstruction, DrScanInstruction,
                    DrStopInstruction, EndDataInstruction, EndProcedureInstruction, ExitInstruction, ExportInstruction,
                    ForInstruction, GotoInstruction, IfInstruction, IntegerInstruction, IrScanInstruction,
                    IrStopInstruction, NextInstruction, PopInstruction, PostDrInstruction, PostIrInstruction,
                    PreDrInstruction, PreIrInstruction, PrintInstruction, ProcedureInstruction, FrequencyInstruction,
                    PushInstruction, StateInstruction, TRSTInstruction, WaitInstruction)

logger = logging.getLogger(__name__)

class StaplExitCode(Exception):
    def __init__(self, code=0):
        self.code = code

class StaplInterpreter:
    class State:
        def __init__(self, pc, procedure):
            self.pc = pc
            self.procedure = procedure
            self.loop_stack = []
            self.scope = CheckedVariableScope()
            self.stack = []

    def __init__(self, ctl, stapl):
        self.stapl = stapl
        self.ctl = ctl
        self.call_stack = []
        self.data_scopes = {}
        self.state = None
        self.ir_stop = State.RUN_TEST_IDLE
        self.dr_stop = State.RUN_TEST_IDLE

    def _assign(self, variable, value):
        assert not self.state is None
        if not variable.last is None:
            assert not variable.first is None
            first = int(variable.first.evaluate(self.state.scope))
            last = int(variable.last.evaluate(self.state.scope))
            logger.debug(f"Setting {variable.name}[{first}:{last}] to {value}...")
            self.state.scope[variable.name].assign(slice(first, last), value)
        elif not variable.first is None:
            first = int(variable.first.evaluate(self.state.scope))
            logger.debug(f"Setting {variable.name}[{first}] to {value}...")
            self.state.scope[variable.name].assign(first, value)
        else:
            logger.debug(f"Setting {variable.name} to {value}...")
            self.state.scope[variable.name].assign(value)

    def execute(self, instruction=None):
        assert not self.state is None
        if instruction is None:
            assert self.state.pc < len(self.stapl.statements)
            instruction = self.stapl.statements[self.state.pc].instruction
            self.state.pc += 1

        logger.debug(f"{instruction.line}: {instruction}")

        if isinstance(instruction, AssignmentInstruction):
            self._assign(instruction.variable, instruction.value.evaluate(self.state.scope))
        elif isinstance(instruction, BooleanInstruction):
            if instruction.length is None:
                if instruction.value is None:
                    v = Bool(0)
                else:
                    v = instruction.value.evaluate(self.state.scope)
                var = Variable(v)
            else:
                if not instruction.value is None:
                    v = instruction.value.evaluate()
                else:
                    v = BoolArray([0] * instruction.length)
                var = ArrayVariable(v)
            self.state.scope[instruction.name] = var
            logger.debug(f"Setting {instruction.name} to {v}...")
        elif isinstance(instruction, CallInstruction):
            self.call_stack.append(self.state)
            self.state = StaplInterpreter.State(self.stapl.procedures[instruction.procedure], instruction.procedure)
        elif isinstance(instruction, DataInstruction):
            pass
        elif isinstance(instruction, DrScanInstruction):
            in_array = instruction.data_array.evaluate(self.state.scope)
            length = int(instruction.length.evaluate(self.state.scope))
            if len(in_array) < length:
                in_array.extend(length)
            elif len(in_array) > length:
                in_array = in_array[length-1:0]
            out_array = self.ctl.dr_scan(in_array.to_bitarray(), self.dr_stop)
            out_array = BoolArray(out_array)
            if not instruction.capture_array is None:
                self._assign(instruction.capture_array, out_array)
            if not instruction.compare_array is None:
                compare_array = instruction.compare_array.evaluate(self.state.scope)
                compare_mask_array = instruction.compare_mask_array.evaluate(self.state.scope)
                if out_array & compare_mask_array == compare_array & compare_mask_array:
                    self._assign(instruction.compare_result, Bool(1))
                else:
                    self._assign(instruction.compare_result, Bool(0))
        elif isinstance(instruction, DrStopInstruction):
            if instruction.state in (State.TEST_LOGIC_RESET, State.RUN_TEST_IDLE, State.PAUSE_IR, State.PAUSE_DR):
                self.dr_stop = instruction.state
            else:
                raise Exception("Invalid state for DRSTOP")
        elif isinstance(instruction, EndDataInstruction):
            return False
        elif isinstance(instruction, EndProcedureInstruction):
            if len(self.call_stack) > 0:
                self.state = self.call_stack.pop()
            else:
                return False
        elif isinstance(instruction, ExitInstruction):
            raise StaplExitCode(instruction.exit_code.evaluate(self.state.scope))
        elif isinstance(instruction, ExportInstruction):
            s = ""
            for part in instruction.parts:
                if isinstance(part, Evaluatable):
                    s += str(part.evaluate(self.state.scope))
                else:
                    s += str(part)
            logger.info(f"EXPORT {instruction.key}: {s}")
            self.ctl.export(instruction.key, s)
        elif isinstance(instruction, ForInstruction):
            start = instruction.start.evaluate(self.state.scope)
            step = instruction.step.evaluate(self.state.scope)
            end = instruction.end.evaluate(self.state.scope)
            self.state.loop_stack.append((instruction.var, step, end, self.state.pc))
            self.state.scope[instruction.var] = var = Variable(start)
        elif isinstance(instruction, FrequencyInstruction):
            self.ctl.set_frequency(int(instruction.frequency.evaluate(self.state.scope)))
        elif isinstance(instruction, GotoInstruction):
            try:
                assert not self.state.procedure is None
                self.state.pc = self.stapl.labels[self.state.procedure][instruction.label]
            except KeyError:
                raise Exception(f"Label {instruction.label} not found")
        elif isinstance(instruction, IfInstruction):
            v = instruction.condition.evaluate(self.state.scope)
            if Bool(v):
                self.execute(instruction.instruction)
        elif isinstance(instruction, IntegerInstruction):
            if instruction.length is None:
                if instruction.value is None:
                    v = Int(0)
                else:
                    v = instruction.value.evaluate(self.state.scope)
                var = Variable(v)
            else:
                assert isinstance(instruction.value, IntArray)
                v = IntArray([0] * instruction.length)
                if not instruction.value is None:
                    for i in range(instruction.length):
                        v[i] = instruction.value[i].evaluate(self.state.scope)
                var = ArrayVariable(v)
            self.state.scope[instruction.name] = var
            logger.debug(f"Setting {instruction.name} to {v}...")
        elif isinstance(instruction, IrScanInstruction):
            in_array = instruction.data_array.evaluate(self.state.scope)
            length = int(instruction.length.evaluate(self.state.scope))
            if len(in_array) < length:
                raise Exception(f"Instruction array of size {len(in_array)} doesn't match length {instruction.length}")
            if len(in_array) != length:
                in_array = in_array[length-1:0]
            out_array = self.ctl.ir_scan(in_array.to_bitarray(), self.ir_stop)
            out_array = BoolArray(out_array)
            if not instruction.capture_array is None:
                self._assign(instruction.capture_array, out_array)
            if not instruction.compare_array is None:
                compare_array = instruction.compare_array.evaluate(self.state.scope)
                compare_mask_array = instruction.compare_mask_array.evaluate(self.state.scope)
                if out_array & compare_mask_array == compare_array & compare_mask_array:
                    self._assign(instruction.compare_result, Bool(1))
                else:
                    self._assign(instruction.compare_result, Bool(0))
        elif isinstance(instruction, IrStopInstruction):
            if instruction.state in (State.TEST_LOGIC_RESET, State.RUN_TEST_IDLE, State.PAUSE_IR, State.PAUSE_DR):
                self.ir_stop = instruction.state
            else:
                raise Exception("Invalid state for IRSTOP")
        elif isinstance(instruction, NextInstruction):
            if len(self.state.loop_stack) == 0:
                raise Exception("NEXT without FOR")
            var, step, end, first_pc = self.state.loop_stack[-1]
            if instruction.var != var:
                raise Exception(f"NEXT variable {instruction.var} doesn't match FOR variable {var}")
            var = self.state.scope[var]
            cur = var.evaluate()
            if (Int(step) > 0 and cur < end) or (Int(step) < 0 and cur > end):
                var.assign(cur + step)
                self.state.pc = first_pc
            else:
                self.state.loop_stack.pop()
        elif isinstance(instruction, PopInstruction):
            v = self.state.stack.pop()
            self._assign(instruction.variable, v)
        elif isinstance(instruction, PrintInstruction):
            s = ""
            for part in instruction.parts:
                if isinstance(part, Evaluatable):
                    s += str(part.evaluate(self.state.scope))
                else:
                    s += str(part)
            print(s)

        elif isinstance(instruction, ProcedureInstruction):
            assert len(self.state.scope) == 0
            for dep in instruction.uses:
                proc = self.stapl.procedures.get(dep)
                data = self.data_scopes.get(dep)
                if (proc is None) and (data is None):
                    raise Exception("Dependency {dep} not found for procedure {instruction.name}")
                elif not ((proc is None) or (data is None)):
                    raise Exception("Dependency {dep} is ambiguous for procedure {instruction.name}")
                if not data is None:
                    self.state.scope.update(data)
        elif isinstance(instruction, PushInstruction):
            self.state.stack.append(instruction.value.evaluate(self.state.scope))
        elif isinstance(instruction, StateInstruction):
            for state in instruction.states:
                self.ctl.enter_state(state)
        elif isinstance(instruction, TRSTInstruction):
            self.ctl.trst(cycles=int(instruction.wait_cycles.evaluate(self.state.scope)),
                          usec=int(instruction.wait_usec.evaluate(self.state.scope)))
        elif isinstance(instruction, WaitInstruction):
            if not instruction.wait_state is None:
                self.ctl.enter_state(instruction.wait_state)
            else:
                self.ctl.enter_state(State.RUN_TEST_IDLE)
            self.ctl.wait(cycles=int(instruction.wait_cycles.evaluate(self.state.scope)),
                          usec=int(instruction.wait_usec.evaluate(self.state.scope)))
            if not instruction.end_state is None:
                self.ctl.enter_state(instruction.end_state)
            else:
                self.ctl.enter_state(State.RUN_TEST_IDLE)
        else:
            raise NotImplementedError(f"{instruction} not implemented")

        return True

    def _run_procedure(self, pc, procedure=None):
        self.state = StaplInterpreter.State(pc, procedure)
        done = False
        while not done:
            done = not self.execute()
        state = self.state
        self.state = None
        return state

    def run(self, action):
        self.ir_stop = State.RUN_TEST_IDLE
        self.dr_stop = State.RUN_TEST_IDLE

        for name, pc in self.stapl.data_blocks.items():
            logger.debug(f"Initializing {name}...")
            self.data_scopes[name] = self._run_procedure(pc).scope
            logger.debug(f"Data {name} initialized")

        logger.info(f"Running action {action}...")
        try:
            action = self.stapl.actions[action]
        except KeyError:
            raise KeyError(f"Action {action} not found")
        for procedure, opt in action.procedures:
            try:
                self._run_procedure(self.stapl.procedures[procedure], procedure)
            except KeyError:
                raise KeyError(f"Procedure {procedure} not found")
            except StaplExitCode as e:
                if e.code == 0:
                    break
                else:
                    raise
        logger.info(f"Action completed")

