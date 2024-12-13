#!/usr/bin/env python3
import os, sys
import argparse
import logging
import random
import time
from bitarray import bitarray
from bitarray.util import int2ba
from pyftdi.ftdi import Ftdi

import swobs

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    drv = swobs.drivers.FT2232H(swobs.drivers.FT2232H.list_devices()[0])
    dev = swobs.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    ctl = swobs.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()

    try:
        dev.pinmap['PB2D'].output_enable()
        while True:
            dev.pinmap['PB2D'].set_value(1)
            ctl.cycle()
            time.sleep(0.5)

            dev.pinmap['PB2D'].set_value(0)
            ctl.cycle()
            time.sleep(0.5)
    finally:
        ctl.reset()
