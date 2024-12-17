#!/usr/bin/env python3
import asyncio
import logging

import ebyst

logger = logging.getLogger(__name__)

async def i2c_test(ctl):
    i2c = ebyst.interfaces.I2C(ctl, dev.pinmap['PB9A'], dev.pinmap['PB4B'])
    await i2c.init()

    dev_address = 0xa0
    reg_address = 0x10
    data = 0xa5
    print(f"Writing {dev_address:02x}:{reg_address:02x} <= {data:02x}")
    await i2c.write(0xa0, 0x10, 0xa5)
    print(f"Reading {dev_address:02x}:{reg_address:02x} => ", end='')
    x = await i2c.read(0xa0, 0x10)
    print(f"{x:02x}")

    assert x == 0xa5

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices()[0])
    dev = ebyst.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    ctl = ebyst.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()

    try:
        asyncio.run(i2c_test(ctl))
    finally:
        ctl.reset()
