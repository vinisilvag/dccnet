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

        synchronization = struct.pack("!II", self.sync, self.sync)
        length = struct.pack("!H", len(data))
        frame_id = struct.pack("!H", id)
        frame_flags = struct.pack("!B", flags)

        frame = synchronization + b"\x00\x00" + length + frame_id + frame_flags + data
        print("frame without chksum defined: ", frame)

        chksum = self.checksum(frame)
        # print("chksum: ", chksum)
        # print("chksum hex: ", hex(chksum))
        checksum = struct.pack("!H", chksum)

        frame = synchronization + checksum + length + frame_id + frame_flags + data
        print("frame with chksum defined", frame)

        return frame, chksum

    def encode_ack(self, id: int):
        synchronization = struct.pack("!II", self.sync, self.sync)
        length = struct.pack("!H", 0)
        frame_id = struct.pack("!H", id)
        frame_flags = struct.pack("!B", 0x80)

        frame = synchronization + b"\x00\x00" + length + frame_id + frame_flags
        print("frame without chksum defined: ", frame)

        chksum = self.checksum(frame)
        # print("chksum: ", chksum)
        # print("chksum hex: ", hex(chksum))
        checksum = struct.pack("!H", chksum)

        frame = synchronization + checksum + length + frame_id + frame_flags
        print("frame with chksum defined", frame)

        return frame, chksum
