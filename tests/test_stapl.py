#!/usr/bin/env python3
import os, sys
import logging

from ebyst.stapl import StaplFile, StaplInterpreter, StaplExitCode
from ebyst import JtagState as State

logger = logging.getLogger(__name__)

def get_all_stapls(root):
    ret = []
    for (root, dirs, files) in os.walk(root):
        for dir in dirs:
            ret += get_all_stapls(dir)
        for file in files:
            if os.path.splitext(file.lower())[-1] in (".stapl", ".stp"):
                ret.append(os.path.join(root, file))
    return ret

class Checker:
    def __init__(self, stapl):
        self.checks = []
        self.exit_code = None
        for note in stapl.notes:
            if note.key == "TEST":
                self.checks.append(str(note.text))
            elif note.key == "EXIT":
                self.exit_code = int(note.text)
        self.total = 0
        self.errors = 0

    def check(self, label):
        if len(self.checks) == 0:
            print(f"CHECK {label} == ??: ", end='')
            print("FAIL")
            self.errors += 1
        else:
            print(f"CHECK {label} == {self.checks[0]}: ", end='')
            if self.checks[0] == str(label):
                print("OK")
            else:
                print("FAIL")
                self.errors += 1
            self.checks.pop(0)
        self.total += 1

    def export(self, key, data):
        if key != "TEST": return
        self.check(data)

    def trst(self, cycles, usec):
        self.check(f"TRST {cycles} CYCLES, {usec} USEC")

    def enter_state(self, state):
        if state == State.TEST_LOGIC_RESET:
            self.check(f"STATE RESET")
        elif state == State.RUN_TEST_IDLE:
            self.check(f"STATE IDLE")
        elif state == State.SELECT_DR_SCAN:
            self.check(f"STATE DRSELECT")
        elif state == State.CAPTURE_DR:
            self.check(f"STATE DRCAPTURE")
        elif state == State.SHIFT_DR:
            self.check(f"STATE DRSHIFt")
        elif state == State.EXIT1_DR:
            self.check(f"STATE DREXIT1")
        elif state == State.PAUSE_DR:
            self.check(f"STATE DRPAUSE")
        elif state == State.EXIT2_DR:
            self.check(f"STATE DREXIT2")
        elif state == State.UPDATE_DR:
            self.check(f"STATE DRUPDATE")
        elif state == State.SELECT_IR_SCAN:
            self.check(f"STATE IRSELECT")
        elif state == State.CAPTURE_IR:
            self.check(f"STATE IRCAPTURE")
        elif state == State.SHIFT_IR:
            self.check(f"STATE IRSHIFT")
        elif state == State.EXIT1_IR:
            self.check(f"STATE IREXIT1")
        elif state == State.PAUSE_IR:
            self.check(f"STATE IRPAUSE")
        elif state == State.EXIT2_IR:
            self.check(f"STATE IREXIT2")
        elif state == State.UPDATE_IR:
            self.check(f"STATE IRUPDATE")
        else:
            print(state)
            assert False

    def wait(self, cycles, usec):
        self.check(f"WAIT {cycles} CYCLES, {usec} USEC")

    def is_done(self):
        return len(self.checks) == 0

def test_action(stapl_file, action):
    chk = Checker(stapl_file)
    interpreter = StaplInterpreter(chk, stapl_file)
    logger.info(f"Running {action}")
    exit_code = None
    try:
        interpreter.run(action)
    except StaplExitCode as e:
        exit_code = e.code
    if not chk.is_done():
        raise Exception(f"EXPORT TEST output count doesn't match NOTE TEST output count")
    if chk.exit_code != exit_code:
        raise Exception(f"EXIT code doesn't match NOTE EXIT output")
    if chk.total == 0:
        raise Exception(f"No checks found")
    if chk.errors > 0:
        raise Exception(f"One or more checks failed")

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    if len(sys.argv) == 1:
        for fn in sorted(get_all_stapls("stapl/tests")):
            logger.info(f"Parsing {fn}")
            with open(fn, "r") as f:
                stapl = StaplFile.parse(f)
            for action in stapl.actions:
                test_action(stapl, action)
    elif len(sys.argv) == 2:
        fn = sys.argv[1]
        logger.info(f"Parsing {fn}")
        with open(fn, "r") as f:
            stapl = StaplFile.parse(f)
        for action in stapl.actions:
            test_action(stapl, action)
    elif len(sys.argv) == 3:
        fn = sys.argv[1]
        logger.info(f"Parsing {fn}")
        with open(fn, "r") as f:
            stapl = StaplFile.parse(f)
        test_action(stapl, sys.argv[2])
    else:
        assert False