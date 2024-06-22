import struct


class DCCNET:
    def __init__(self) -> None:
        self.sync = 0xDCC023C2

    def checksum(self, data: bytes) -> int:
        if len(data) % 2 == 1:
            data += b"\x00"

        checksum = 0
        for i in range(0, len(data), 2):
            word = data[i] + (data[i + 1] << 8)  # 16-bit wide word
            checksum += word
            checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum = ~checksum & 0xFFFF

        return checksum

    def encode(self, data: bytes, id: int, flags: int) -> tuple[bytes, int]:
        # print("data: ", data)
        # print("length: ", len(data))

        frame = struct.pack(
            f">IIHHHB{len(data)}s", self.sync, self.sync, 0, len(data), id, flags, data
        )
        # print("frame without chksum defined: ", frame)

        chksum = self.checksum(frame)
        # print("chksum: ", chksum)
        # print("chksum hex: ", hex(chksum))
        checksum = struct.pack("<H", chksum)

        frame = struct.pack(
            f">II2sHHB{len(data)}s",
            self.sync,
            self.sync,
            checksum,
            len(data),
            id,
            flags,
            data,
        )
        # print("frame with chksum defined", frame)

        return frame, chksum

    def encode_ack(self, id: int):
        frame, chksum = self.encode(b"", id, 0x80)
        return frame, chksum
