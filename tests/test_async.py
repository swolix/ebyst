#!/usr/bin/env python3
import asyncio
import logging

import ebyst

logger = logging.getLogger(__name__)

async def loopback_test(ctl, opin, ipin, count):
    opin.output_enable(True)
    ipin.output_enable(False)

    for i in range(count):
        if i > 1: assert i & 1 == ipin.get_value()
        opin.set_value(i & 1)
        await ctl.cycle()

async def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices()[0])
    dev = ebyst.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    ctl = ebyst.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(loopback_test(ctl, dev.pinmap['PB2C'], dev.pinmap['PB2A'], 100))
        tg.create_task(loopback_test(ctl, dev.pinmap['PB4C'], dev.pinmap['PB4D'], 70))
    assert ctl.cycle_counter == 100

if __name__ == "__main__":
    asyncio.run(main())