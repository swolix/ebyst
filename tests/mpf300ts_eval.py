#!/usr/bin/env python3
import logging
import asyncio
import time
from bitarray import bitarray
from bitarray.util import int2ba

import ebyst

from ebyst.interfaces import MT25QU01GBBB

logger = logging.getLogger(__name__)


async def leds(ctl, dev):
    LEDS = ['IO_H21', 'IO_H22', 'IO_F23', 'IO_C27', 'IO_D25', 'IO_C26', 'IO_B26', 'IO_F22']
    while True:
        for pin in LEDS + LEDS[::-1]:
            dev.pinmap[pin].output_enable()
            dev.pinmap[pin].set_value(1)
            await ctl.cycle()
            dev.pinmap[pin].set_value(0)

async def flash(ctl, dev):
    flash = MT25QU01GBBB(ctl, C=dev.pinmap["IO_H19"], Sn=dev.pinmap["IO_A20"], RESETn=dev.pinmap["IO_A24"],
                              WPn=dev.pinmap["IO_A27"], HOLDn=dev.pinmap["IO_A22"],
                              DQ0=dev.pinmap["IO_G19"], DQ1=dev.pinmap["IO_C18"])

    await flash.init()
    print("Flash ID:", (await flash.read_id()).hex())

async def main():
    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices([(0x1514, 0x2008)])[0])
    dev = ebyst.Device.from_bsdl("bsdl/MPF300TSFCG1152.bsdl")
    ctl = ebyst.TapController(drv)

    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(leds(ctl, dev))
            tg.create_task(flash(ctl, dev))
    except KeyboardInterrupt:
        pass
    finally:
        ctl.reset()

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    asyncio.run(main())