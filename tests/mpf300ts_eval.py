#!/usr/bin/env python3
import logging
import asyncio
import time
from bitarray import bitarray
from bitarray.util import int2ba

import ebyst

logger = logging.getLogger(__name__)

LEDS = ['IO_H21', 'IO_H22', 'IO_F23', 'IO_C27', 'IO_D25', 'IO_C26', 'IO_B26', 'IO_F22']

async def leds(ctl):
    while True:
        for pin in LEDS + LEDS[::-1]:
            dev.pinmap[pin].output_enable()
            dev.pinmap[pin].set_value(1)
            await ctl.cycle()
            dev.pinmap[pin].set_value(0)
            time.sleep(0.05)

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices([(0x1514, 0x2008)])[0])
    dev = ebyst.Device.from_bsdl("bsdl/MPF300TSFCG1152.bsdl")
    ctl = ebyst.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()

    try:
        asyncio.run(leds(ctl))
    except KeyboardInterrupt:
        pass
    finally:
        ctl.reset()
