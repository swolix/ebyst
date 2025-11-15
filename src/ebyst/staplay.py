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
import os, sys
import logging
import argparse

import ebyst
from ebyst.stapl import StaplFile, StaplInterpreter

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

    def __init__(self, *args, color=True, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self.color = color

    def format(self, record):
        if self.color:
            log_color = self.COLORS.get(record.levelname, self.RESET)
            reset = self.RESET
        else:
            log_color = reset = ""
        record.levelname = f"{log_color}{record.levelname}{reset}"
        record.msg = f"{log_color}{record.msg}{reset}"
        return super().format(record)

logger = logging.getLogger(__name__)

def main():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = ColorFormatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S", color=os.isatty(sys.stderr.fileno()))
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    for url in ebyst.drivers.MPSSE.list_devices([(0x1514, 0x2008)]):
        logger.info("Found device: %s", url)

    parser = argparse.ArgumentParser()
    parser.add_argument("device_url", type=str, help="FTDI URL")
    parser.add_argument("stapl_file", type=str, help="STAPL file")
    parser.add_argument("action", type=str, nargs='+', help="action(s) to perform")
    parser.add_argument("--optional", type=bool, default=False, help="Perform optional steps (default: false)")
    args = parser.parse_args()

    drv = ebyst.drivers.MPSSE(args.device_url)
    ctl = ebyst.TapController(drv)

    logger.info("Parsing stapl...")
    with open(args.stapl_file, "r") as f:
        stapl = StaplFile.parse(f)
    logger.info("Done")

    logger.info("Start running")
    interpreter = StaplInterpreter(ctl, stapl)
    for action in args.action:
        logger.info(f"Running action {action}")
        interpreter.run(action, optional=args.optional)

if __name__ == "__main__":
    main()
