
class Crc:
    CCITT_CRC =  0x8408

    def __init__(self):
        self.crc = 0xffff

    def update(self, s):
        for in_byte in s:
            in_byte = ord(in_byte)
            if in_byte != 13:
                for _ in range(8):
                    feedback = (in_byte ^ self.crc) & 0x01;
                    self.crc >>= 1; # shift the shift register
                    if feedback: self.crc ^= Crc.CCITT_CRC; # invert selected bits
                    in_byte >>= 1; # get the next bit of in_byte

    def finalize(self):
        return (~self.crc) & 0xFFFF
