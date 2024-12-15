#!/usr/bin/env python3
import asyncio
import logging

import ebyst

logger = logging.getLogger(__name__)

async def lb_test(ctl):
    await ctl.cycle()

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    dev1 = ebyst.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    dev2 = ebyst.Device.from_bsdl("bsdl/MPF100Tfcg484.bsdl")
    dev3 = ebyst.Device.from_bsdl("bsdl/XA3S400_FG456.bsdl")
    sim1 = ebyst.drivers.Sim(dev1)
    sim2 = ebyst.drivers.Sim(dev2)
    sim3 = ebyst.drivers.Sim(dev3)
    sim_chain = ebyst.drivers.SimChain([sim1, sim2, sim3])
    ctl = ebyst.TapController(sim_chain)
    ctl.detect_chain()
    ctl.add_device(dev1)
    ctl.add_device(dev2)
    ctl.add_device(dev3)
    ctl.validate_chain()
    ctl.extest()

    try:
        asyncio.run(lb_test(ctl))
    finally:
        ctl.reset()
