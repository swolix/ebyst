#!/usr/bin/env python3
#
# Control LEDs of MPF300TS eval kit via FlashPro Express
#
# Flashpro tcl script (execute with 'FPExpress SCRIPT:flashpro.tcl');
#
# file delete -force tmp
# new_project -name fp -location tmp -mode single
# set_programming_file -file {flashpro.stp}
# set_programming_action -action {BSCAN}
# run_selected_actions
# close_project

import logging
import asyncio
import sys

from bitarray import bitarray
from bitarray.util import int2ba, ba2int

import ebyst

from ebyst.interfaces import MT25Q, MDIO, DDR3, DDR4
from ebyst import Pin, PinGroup, DiffPin

logger = logging.getLogger(__name__)

async def leds(dev):
    LEDS_ON = ['IO_H21', 'IO_H22', 'IO_F23', 'IO_C27']
    LEDS_OFF = ['IO_D25', 'IO_C26', 'IO_B26', 'IO_F22']
    for pin in LEDS_ON:
        dev.pinmap[pin].output_enable()
        dev.pinmap[pin].set_value(True)
    for pin in LEDS_OFF:
        dev.pinmap[pin].output_enable()
        dev.pinmap[pin].set_value(False)
    await dev.ctl.cycle()
    await asyncio.sleep(2.0)

async def main():
    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices([(0x1514, 0x2008)])[0])
    dev = ebyst.Device.from_bsdl("bsdl/MPF300TSFCG1152.bsdl")
    ctl = ebyst.TapController(drv)

    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()

    ctl.start_stapl_recording(sys.stdout)

    try:
        ctl.extest()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(leds(dev))

    except KeyboardInterrupt:
        pass
    finally:
        ctl.stop_stapl_recording(reset=False)
        ctl.reset()

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    asyncio.run(main())