# EByST
Boundary scan test framework for board validation

# Basic example
```python
# initialize JTAG interface driver (currently only FTDI chips with MPSSE are supported)
drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices()[0])
ctl = ebyst.TapController(drv)
ctl.detect_chain()

# Add device(s) to chain
dev = ebyst.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
ctl.add_device(dev)
ctl.validate_chain()

# Start test
ctl.extest()

# Loopback test (assuming loopback on pins
dev.pinmap['O'].output_enable(True)
dev.pinmap['I'].output_enable(False)
dev.pinmap['O'].set_value(1)
await ctl.cycle() # drive output
await ctl.cycle() # sample input
print(dev.pinmap['I'].get_value())
dev.pinmap['O'].set_value(0)
await ctl.cycle() # drive output
await ctl.cycle() # sample input
print(dev.pinmap['I'].get_value())

# I2C test
i2c = ebyst.interfaces.I2C(ctl, dev.pinmap['PB9A'], dev.pinmap['PB4B'])
await i2c.init()
dev_address = 0xa0
reg_address = 0x10
data = 0xa5
print(f"Writing {dev_address:02x}:{reg_address:02x} <= {data:02x}")
await i2c.write(0xa0, 0x10, 0xa5)
print(f"Reading {dev_address:02x}:{reg_address:02x} => ", end='')
await x = i2c.read(0xa0, 0x10)
print(f"{x:02x}")

ctl.reset()
```
# Async
The library uses `asyncio` to allow running multiple tests in parallel.
When the loopback test and I2C test above are put in different tasks, they share the same boundary scan cycles,
meaning they run completely parallel
(Note that this only works when they are not using different pins, if pins are shared between tests, make sure to
schedule them appropriately)

Example;
```python
async def main():
    drv = ebyst.drivers.MPSSE(ebyst.drivers.MPSSE.list_devices()[0])
    dev = ebyst.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
    ctl = ebyst.TapController(drv)
    ctl.detect_chain()
    ctl.add_device(dev)
    ctl.validate_chain()
    ctl.extest()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(loopback_test(ctl, dev.pinmap['PB2C'], dev.pinmap['PB2A']))
        tg.create_task(loopback_test(ctl, dev.pinmap['PB4C'], dev.pinmap['PB4D']))

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    asyncio.run(main())
```

see also `tests/test_async.py`

# Tracing
Generate .vcd traces for selected pins;
```python
    pins = {
        'MDC':      dev.pinmap["IO_Y12"],
        'MDIO':     dev.pinmap["IO_Y13"],
    }
    ctl.trace("mdio.vcd", **pins)
    mdio = MDIO(ctl, **pins)
```