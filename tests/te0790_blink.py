#!/usr/bin/env python3
import logging
import asyncio
import time
from bitarray import bitarray
from bitarray.util import int2ba
from pyftdi.ftdi import Ftdi

import ebyst

logger = logging.getLogger(__name__)

async def blink(ctl):
    dev.pinmap['PB2D'].output_enable()
    while True:
        dev.pinmap['PB2D'].set_value(1)
        await ctl.cycle()
        time.sleep(0.5)

        dev.pinmap['PB2D'].set_value(0)
        await ctl.cycle()
        time.sleep(0.5)

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices()[0])
    dev = ebyst.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    ctl = ebyst.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()

    try:
        asyncio.run(blink(ctl))
    except KeyboardInterrupt:
        pass
    finally:
        ctl.reset()
