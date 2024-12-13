#!/usr/bin/env python3
import os, sys
import argparse
import logging
import random
import time
from bitarray import bitarray
from bitarray.util import int2ba

import swobs

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    drv = swobs.drivers.FT2232H(swobs.drivers.FT2232H.list_devices()[0])
    dev = swobs.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    ctl = swobs.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()

    i2c = swobs.interfaces.I2C(ctl, dev.pinmap['PB9A'], dev.pinmap['PB4B'])
    i2c.init()
    try:
        dev_address = 0xa0
        reg_address = 0x10
        data = 0xa5
        print(f"Writing {dev_address:02x}:{reg_address:02x} <= {data:02x}")
        i2c.write(0xa0, 0x10, 0xa5)
        print(f"Reading {dev_address:02x}:{reg_address:02x} => ", end='')
        x = i2c.read(0xa0, 0x10)
        print(f"{data:02x}")

        assert x == 0xa5
    finally:
        ctl.reset()
