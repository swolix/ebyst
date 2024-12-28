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

# MT0 = XOR (A1, A6, PAR)
# MT1 = XOR (A8, ALERT_n, A9)
# MT2 = XOR (A2, A5, A13)
# MT3 = XOR (A0 A7, A11)
# MT4 = XOR (CK_c, ODT, CAS_n/A15)
# MT5 = XOR (CKE, RAS_n,/A16, A10/AP)
# MT6 = XOR (ACT_n, A4, BA1)
# MT7 = XOR (BG1, DM, CK_t)
# MT8 = XOR (WE_n / A14, A12 / BC, BA0)
# MT9 = XOR (BG0, A3, (RESET_n and TEN))


# DQ0 = MT0
# DQ1 = MT1
# DQ2 = MT2
# DQ3 = MT3
# DQ4 = MT4
# DQ5 = MT5
# DQ6 = MT6
# DQ7 = MT7
# DQS_t = MT8
# DQS_c = MT9


class DDR4:
    def __init__(self, ctl,
                 RESETn: Pin,
                 TEN: Pin,
                 CK: DiffPin,
                 CKE: Pin | PinGroup,
                 CSn: Pin | PinGroup,
                 CASn: Pin,
                 RASn: Pin,
                 WEn: Pin,
                 BG: PinGroup,
                 A: PinGroup,
                 BA: PinGroup,
                 DQ: PinGroup,
                 DQS: DiffPin,
                 ODT: PinGroup,
                 ACTn: Pin,
                 PARITY: Pin,
                 ALERTn: Pin,
                 DM: Pin):
        self.ctl = ctl
        self.RESETn = RESETn
        self.CK = CK
        self.CKE = CKE
        self.CSn = CSn
        self.RASn = RASn
        self.CASn = CASn
        self.WEn = WEn
        self.BG = BG
        self.A = A
        self.BA = BA
        self.DQ = DQ
        self.DQS = DQS
        self.ODT = ODT
        self.DM = DM
        self.ACTn = ACTn
        self.PARITY = PARITY
        self.ALERTn = ALERTn
        self.TEN = TEN

        # Connectivity test connections
        self.MT = {
            self.DQ[0]: (self.A[1], self.A[6], self.PARITY),
            self.DQ[1]: (self.A[8], self.ALERTn, self.A[9]),
            self.DQ[2]: (self.A[2], self.A[5], self.A[13]),
            self.DQ[3]: (self.A[0], self.A[7], self.A[11]),
            self.DQ[4]: (self.CK[1], self.ODT, self.CASn),
            self.DQ[5]: (self.CKE, self.RASn, self.A[10]),
            self.DQ[6]: (self.ACTn, self.A[4], self.BA[1]),
            self.DQ[7]: (self.BG[1], self.DM, self.CK[0]),
            self.DQS[0]: (self.WEn, self.A[12], self.BA[0]),
            self.DQS[1]: (self.BG[0], self.A[3], self.RESETn),
        }

    async def cycle(self, count=1):
        for i in range(count):
            self.CK.set_value(1)
            await self.ctl.cycle()
            self.CK.set_value(0)
            await self.ctl.cycle()

    async def init(self):
        self.CK.output_enable(True)
        self.CK.set_value(0)
        self.RESETn.output_enable(True)
        self.RESETn.set_value(0)
        self.CKE.output_enable(True)
        self.CKE.set_value(0)
        self.CSn.output_enable(True)
        self.CSn.set_value(3)
        self.DQ.output_enable(False)
        self.DQS.output_enable(False)
        self.A.output_enable(True)
        self.BA.output_enable(True)
        self.BG.output_enable(True)
        self.RASn.output_enable(True)
        self.RASn.set_value(1)
        self.CASn.output_enable(True)
        self.CASn.set_value(1)
        self.ACTn.output_enable(True)
        self.ACTn.set_value(1)
        self.ALERTn.output_enable(True)
        self.ALERTn.set_value(1)
        self.PARITY.output_enable(True)
        self.PARITY.set_value(0)
        self.WEn.output_enable(True)
        self.WEn.set_value(1)
        self.ODT.output_enable(True)
        self.ODT.set_value(0)
        self.DM.output_enable(True)
        self.DM.set_value(0)
        self.TEN.output_enable(True)
        self.TEN.set_value(1)
        self.RESETn.set_value(0)
        await self.ctl.cycle()
        self.RESETn.set_value(1)

    async def test(self):
        self.CSn.set_value(0)

        # all zero
        for v in self.MT.values():
            for i in range(3):
                v[i].set_value(0)
        await self.ctl.cycle()

        for v in self.MT.values():
            v[0].set_value(1)
        await self.ctl.cycle()
        for v in self.MT.keys():
            if v.get_value() != 0:
                raise Exception(f"Connectivity test failed on {self.MT[v][0].name} / {self.MT[v][1].name} / {self.MT[v][2].name} => {v.name}")

        for v in self.MT.values():
            v[1].set_value(1)
        await self.ctl.cycle()
        for v in self.MT.keys():
            if v.get_value() != 1:
                raise Exception(f"Connectivity test failed on {self.MT[v][0].name} => {v.name}")

        for v in self.MT.values():
            v[2].set_value(1)
        await self.ctl.cycle()
        for v in self.MT.keys():
            if v.get_value() != 0:
                raise Exception(f"Connectivity test failed on {self.MT[v][1].name} => {v.name}")

        await self.ctl.cycle()
        for v in self.MT.keys():
            if v.get_value() != 1:
                raise Exception(f"Connectivity test failed on {self.MT[v][2].name} => {v.name}")

        # TODO test for signals stuck together