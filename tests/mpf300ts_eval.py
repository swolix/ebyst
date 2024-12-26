#!/usr/bin/env python3
import logging
import asyncio
import time
import random

from bitarray import bitarray
from bitarray.util import int2ba, ba2int

import ebyst

from ebyst.interfaces import MT25QU01GBBB, MDIO, DDR3
from ebyst import Pin, PinGroup, DiffPin

logger = logging.getLogger(__name__)


async def leds(ctl, dev):
    LEDS = ['IO_H21', 'IO_H22', 'IO_F23', 'IO_C27', 'IO_D25', 'IO_C26', 'IO_B26', 'IO_F22']
    for i in range(10):
        for pin in LEDS + LEDS[::-1]:
            dev.pinmap[pin].output_enable()
            dev.pinmap[pin].set_value(1)
            await ctl.cycle()
            dev.pinmap[pin].set_value(0)

async def flash(ctl, dev):
    pins = {
        'C':        dev.pinmap["IO_H19"],
        'Sn':       dev.pinmap["IO_A20"],
        'RESETn':   dev.pinmap["IO_A24"],
        'WPn':      dev.pinmap["IO_A27"],
        'HOLDn':    dev.pinmap["IO_A22"],
        'DQ0':      dev.pinmap["IO_G19"],
        'DQ1':      dev.pinmap["IO_C18"],
    }
    ctl.trace("flash.vcd", **pins)
    flash = MT25QU01GBBB(ctl, **pins)

    await flash.init()
    print("Flash ID:", (await flash.read_id()).hex())

async def mdio(ctl, dev):
    pins = {
        'MDC':      dev.pinmap["IO_Y12"],
        'MDIO':     dev.pinmap["IO_Y13"],
    }
    ctl.trace("mdio.vcd", **pins)
    mdio = MDIO(ctl, **pins)

    # PHY ID
    for pin in ("IO_Y7", "IO_AA7", "IO_AA9"):
        dev.pinmap[pin].output_enable()
        dev.pinmap[pin].set_value(0)

    # PHY RESET
    dev.pinmap["IO_U11"].output_enable()
    dev.pinmap["IO_U11"].set_value(0)
    await ctl.cycle()
    dev.pinmap["IO_U11"].set_value(1)
    await ctl.cycle()

    await mdio.init()
    print("PHY ID: 0x%04x %04x" % (await mdio.read(0, 2), await mdio.read(0, 3)))

async def ddr3(ctl, dev):
    pins = {
        'DQ':       PinGroup([dev.pinmap["IO_AN22"], dev.pinmap["IO_AM24"], dev.pinmap["IO_AN21"], dev.pinmap["IO_AN24"],
                              dev.pinmap["IO_AP20"], dev.pinmap["IO_AP19"], dev.pinmap["IO_AP21"], dev.pinmap["IO_AN19"]]),
        'DQS':      DiffPin(dev.pinmap["IO_AP23"], dev.pinmap["IO_AP24"]),
        'DM':       dev.pinmap["IO_AN23"],
        'A':        PinGroup([dev.pinmap["IO_AL27"], dev.pinmap["IO_AL26"], dev.pinmap["IO_AM27"], dev.pinmap["IO_AN27"],
                              dev.pinmap["IO_AN26"], dev.pinmap["IO_AP25"], dev.pinmap["IO_AL25"], dev.pinmap["IO_AK25"],
                              dev.pinmap["IO_AJ23"], dev.pinmap["IO_AH23"], dev.pinmap["IO_AJ25"], dev.pinmap["IO_AJ24"],
                              dev.pinmap["IO_AL22"], dev.pinmap["IO_AK23"], dev.pinmap["IO_AL24"], dev.pinmap["IO_AL23"]]),
        'BA':       PinGroup([dev.pinmap["IO_AE25"], dev.pinmap["IO_AD23"], dev.pinmap["IO_AD25"]]),
        'ODT':      PinGroup([dev.pinmap["IO_AF23"], dev.pinmap["IO_AH25"]]),
        'CK':       DiffPin(dev.pinmap["IO_AP26"], dev.pinmap["IO_AP27"]),
        'CKE':      PinGroup([dev.pinmap["IO_AF22"], dev.pinmap["IO_AD24"]]),
        'CSn':      PinGroup([dev.pinmap["IO_AE22"], dev.pinmap["IO_AH24"]]),
        'RASn':     dev.pinmap["IO_AE23"],
        'CASn':     dev.pinmap["IO_AF25"],
        'WEn':      dev.pinmap["IO_AF24"],
        'RESETn':   dev.pinmap["IO_AG22"],
    }
    ctl.trace("ddr3.vcd", **pins)
    ddr3 = DDR3(ctl, **pins)

    bank = bitarray("000")
    row = bitarray("0000000000000000")
    column = bitarray("0000000000000000")

    await ddr3.init()
    await ddr3.activate(ba=bank, ra=row)
    wdata = []
    for i in range(8):
        wdata.append(int2ba(random.randint(0,256), 8))
    print(f"DDR: Writing: {' '.join(['%02x' % ba2int(x) for x in wdata])}")
    await ddr3.write(ba=bank, ca=column, data=wdata)
    rdata = await ddr3.read(ba=bank, ca=column)
    await ddr3.precharge(ba=bank)
    print(f"DDR: Writing: {' '.join(['%02x' % ba2int(x) for x in rdata])}")
    if rdata == wdata:
        print(f"DDR: OK")
    else:
        print(f"DDR: FAILED")

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
            tg.create_task(mdio(ctl, dev))
            tg.create_task(ddr3(ctl, dev))
    except KeyboardInterrupt:
        pass
    finally:
        ctl.reset()

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    asyncio.run(main())