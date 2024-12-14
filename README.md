# SWOBS
Boundary scan test framework for board validation

# Example
```python
# initialize JTAG interface driver (currently only FT2232H is supported)
drv = swobs.drivers.FT2232H(swobs.drivers.FT2232H.list_devices()[0])
ctl = swobs.TapController(drv)
ctl.detect_chain()

# Add device(s) to chain
dev = swobs.Device.from_bsdl("bsdl/BSDLLCMXO2-256HCQFN32.BSM")
ctl.add_device(dev)
ctl.validate_chain()

# Start test
ctl.extest()

# Loopback test (assuming loopback on pins
dev.pinmap['O'].output_enable(True)
dev.pinmap['I'].output_enable(False)
dev.pinmap['O'].set_value(1)
ctl.cycle() # drive output
ctl.cycle() # sample input
print(dev.pinmap['I'].get_value())
dev.pinmap['O'].set_value(0)
ctl.cycle() # drive output
ctl.cycle() # sample input
print(dev.pinmap['I'].get_value())

# I2C test
i2c = swobs.interfaces.I2C(ctl, dev.pinmap['PB9A'], dev.pinmap['PB4B'])
i2c.init()
dev_address = 0xa0
reg_address = 0x10
data = 0xa5
print(f"Writing {dev_address:02x}:{reg_address:02x} <= {data:02x}")
i2c.write(0xa0, 0x10, 0xa5)
print(f"Reading {dev_address:02x}:{reg_address:02x} => ", end='')
x = i2c.read(0xa0, 0x10)
print(f"{x:02x}")

ctl.reset()
```