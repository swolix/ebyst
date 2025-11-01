#!/usr/bin/env python3
import os, sys
import logging

from ebyst.stapl import StaplFile, StaplInterpreter, StaplExitCode
from ebyst import JtagState as State

class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels."""

    # Define color codes
    COLORS = {
        "DEBUG": "\033[0;90m",
        "INFO": "\033[1;97m",
        "WARNING": "\033[1;33m",
        "ERROR": "\033[1;31m",
        "CRITICAL": "\033[1;41m"
    }

    RESET = "\033[0;0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        record.msg = f"{log_color}{record.msg}{self.RESET}"
        return super().format(record)

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
            logger.error(f"CHECK {label} == ??: FAIL")
            self.errors += 1
        else:
            if self.checks[0] == str(label):
                logger.debug(f"CHECK {label} == {self.checks[0]}: OK")
            else:
                logger.error(f"CHECK {label} == {self.checks[0]}: FAIL")
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

    def ir_scan(self, ir, end_state):
        self.check(f"IR SCAN {ir.to01()[::-1]}")
        self.enter_state(end_state)
        return ir

    def dr_scan(self, dr, end_state):
        self.check(f"DR SCAN {dr.to01()[::-1]}")
        self.enter_state(end_state)
        return dr

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
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = ColorFormatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

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