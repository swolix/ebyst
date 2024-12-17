#!/usr/bin/env python3
import logging
import random

from bitarray import bitarray

import ebyst

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    drv = ebyst.drivers.MPSSE("ftdi://ftdi:2232:251633009FEC/1")
    drv.test()
