# Copyright (c) 2024 Sijmen Woutersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import asyncio

from bitarray import bitarray

from ..device import Pin, PinGroup, DiffPin

ON_FALLING = 0
BEFORE_RISING = 1
ON_RISING = 2
BEFORE_FALLING = 3

class DDR3:
    def __init__(self, ctl,
                 RESETn: Pin, 
                 CK: DiffPin,
                 CKE: Pin | PinGroup,
                 CSn: Pin | PinGroup,
                 CASn: Pin,
                 RASn: Pin,
                 WEn: Pin,
                 A: PinGroup,
                 BA: PinGroup,
                 DQ: PinGroup,
                 DQS: DiffPin,
                 ODT: PinGroup,
                 DM: PinGroup):
        self.ctl = ctl
        self.RESETn = RESETn
        self.CK = CK
        self.CKE = CKE
        self.CSn = CSn
        self.RASn = RASn
        self.CASn = CASn
        self.WEn = WEn
        self.A = A
        self.BA = BA
        self.DQ = DQ
        self.DQS = DQS
        self.ODT = ODT
        self.DM = DM
        self.cycle = None

    async def cycle_ck(self):
        self.CK.output_enable(True)
        while True:
            self.CK.set_value(0)
            self.cycle = ON_FALLING
            await self.ctl.cycle()
            self.cycle = BEFORE_RISING
            await self.ctl.cycle()
            self.CK.set_value(1)
            self.cycle = ON_RISING
            await self.ctl.cycle()
            self.cycle = BEFORE_FALLING
            await self.ctl.cycle()

    async def wait_cycle(self, cycle):
        while True:
            await self.ctl.cycle()
            if self.cycle == cycle: break

    async def before_rising_ck(self):
        await self.wait_cycle(BEFORE_RISING)

    async def after_rising_ck(self):
        await self.wait_cycle(BEFORE_FALLING)

    async def cmd_cycle(self, **pins):
        await self.before_rising_ck()

        for name, value in pins.items():
            o = getattr(self, name)
            if isinstance(o, list) or isinstance(o, tuple):
                for i in range(len(o)):
                    o[i].set_value(int(value[i]))
            else:
                o.set_value(int(value))

        await self.after_rising_ck()

        self.RASn.set_value(1)
        self.CASn.set_value(1)
        self.WEn.set_value(1)
        for CSn in self.CSn:
            CSn.set_value(1)

    async def init(self):
        self.task = asyncio.create_task(self.cycle_ck())

        self.RESETn.output_enable(True)
        self.RESETn.set_value(0)
        self.CKE.output_enable(True)
        self.CKE.set_value(0)
        self.CSn.output_enable(True)
        self.CSn.set_value(1)
        self.DQ.output_enable(False)
        self.DQS.output_enable(False)
        self.A.output_enable(True)
        self.BA.output_enable(True)
        self.RASn.output_enable(True)
        self.RASn.set_value(1)
        self.CASn.output_enable(True)
        self.CASn.set_value(1)
        self.WEn.output_enable(True)
        self.WEn.set_value(1)
        self.ODT.output_enable(True)
        self.ODT.set_value(0)
        self.DM.output_enable(True)
        self.DM.set_value(0)

        await self.cmd_cycle()
        self.RESETn.set_value(1)
        await self.cmd_cycle()
        await self.cmd_cycle()
        await self.cmd_cycle()
        await self.cmd_cycle()
        await self.cmd_cycle()
        for CKE in self.CKE:
            CKE.set_value(1)
        await self.cmd_cycle()

        # mr2
        mr2 = bitarray("0" * len(self.A))
        mr2[3:6] = bitarray("100") # CWL = 6
        await self.cmd_cycle(CSn="00", RASn=0, CASn=0, WEn=0, BA="010"[::-1], A=mr2)
        for i in range(4): await self.cmd_cycle()
        # mr3
        mr3 = bitarray("0" * len(self.A))
        await self.cmd_cycle(CSn="00", RASn=0, CASn=0, WEn=0, BA="011"[::-1], A=mr3)
        for i in range(4): await self.cmd_cycle()
        # mr1
        mr1 = bitarray("0" * len(self.A))
        mr1[0] = 1 # DLL = Disable
        mr1[3:5] = bitarray("00") # AL = 0
        await self.cmd_cycle(CSn="00", RASn=0, CASn=0, WEn=0, BA="001"[::-1], A=mr1)
        for i in range(4): await self.cmd_cycle()
        # mr0
        mr0 = bitarray("0" * len(self.A))
        mr0[0:2] = bitarray("00") # BL = Fixed BL8
        mr0[3] = 0 # BT = Sequential
        mr0[4:7] = bitarray("010") # CL = 6
        mr0[8] = 0 # DLL
        mr0[9:12] = bitarray("010") # WR = 6
        mr0[12] = 0 # PD
        await self.cmd_cycle(CSn="00", RASn=0, CASn=0, WEn=0, BA="000"[::-1], A=mr0)
        for i in range(12): await self.cmd_cycle()

    async def activate(self, ba=bitarray("000"), ra=bitarray("0000000000000000")):
        """Activate a row for reading or writing"""
        await self.cmd_cycle(CSn="00", RASn=0, BA=ba, A=ra)
        for i in range(6): await self.cmd_cycle()

    async def read(self, ba=bitarray("000"), ca=bitarray("0000000000000000")):
        """Read from active row"""
        r = []
        await self.cmd_cycle(CSn="00", CASn=0, BA=ba, A=ca)
        
        for i in range(20):
            if self.DQS.get_value() == 0: break
            await self.ctl.cycle()
        
        if self.DQS.get_value() == 1: raise Exception("Read timeout")

        for i in range(4):
            while self.DQS.get_value() == 0:
                await self.ctl.cycle()
            r.append(self.DQ.get_value())
            while self.DQS.get_value() == 1:
                await self.ctl.cycle()
            r.append(self.DQ.get_value())

        for i in range(6): await self.cmd_cycle()

        return r

    async def write(self, ba, ca, data, dm=0):
        """Write to active row"""
        await self.cmd_cycle(CSn="00", CASn=0, WEn=0, BA=ba, A=ca)
        for i in range(5):
            await self.cmd_cycle()
            
        self.DQ.output_enable(True)
        self.DQS.output_enable(True)
        self.DQS.set_value(0xFF)
        self.DM.set_value(dm)

        await self.ctl.cycle()

        for i in range(4):
            self.DQS.set_value(0)
            await self.ctl.cycle()
            self.DQ.set_value(data[2*i])
            await self.ctl.cycle()
            self.DQS.set_value(1)
            await self.ctl.cycle()
            self.DQ.set_value(data[2*i+1])
            await self.ctl.cycle()

        self.DQS.set_value(0)
        await self.ctl.cycle()

        self.DQ.output_enable(False)
        self.DQS.output_enable(False)
        
        for i in range(6): await self.cmd_cycle()

    async def precharge(self, ba=bitarray("000")):
        """Precharge active row (deactivating it)"""
        await self.cmd_cycle(CSn="00", RASn=0, WEn=0, BA=ba)
        for i in range(6): await self.cmd_cycle()
