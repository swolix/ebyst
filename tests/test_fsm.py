#!/usr/bin/env python3
import logging
import random

from bitarray import bitarray

import swobs

logger = logging.getLogger(__name__)

def test_fsm(count=10000):
    dev = swobs.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")

    for state in swobs.JtagState.__members__.values():
        sim = swobs.drivers.Sim(dev)
        ctl = swobs.TapController(sim)
        ctl._goto(state)
        if ctl.state != state or sim.state != state:
            logger.error(f"Incorrect state: target: {swobs.JtagState(state).name}, controller: {ctl.state.name}, sim: {sim.state.name}")
            assert False

    sim = swobs.drivers.Sim(dev)
    ctl = swobs.TapController(sim)
    states = list(swobs.JtagState.__members__.values())

    for i in range(count):
        state = states[random.randint(0, len(states)-1)]
        ctl._goto(state)
        if ctl.state != state or sim.state != state:
            logger.error(f"Incorrect state: target: {swobs.JtagState(state).name}, controller: {ctl.state.name}, sim: {sim.state.name}")
            assert False

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    test_fsm()
