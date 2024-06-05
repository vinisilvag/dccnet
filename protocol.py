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

    def encode(self, data: bytes, id: int) -> bytes:
        #      32       32       16        16       8     8      length
        # 0        32       64        80        96    104   112   112+length
        # +---/----+---/----+---------+---------+-----+-----+------ ... ---+
        # |  SYNC  |  SYNC  | chksum  | length  | ID  |flags| DATA         |
        # +---/----+---/----+---------+---------+-----+-----+------ ... ---+

        print("data: ", data)
        print("length: ", len(data))

        double_sync = struct.pack("!II", self.sync, self.sync)
        payload_length = struct.pack("!H", len(data))
        frame_id = struct.pack("B", id)
        flags = struct.pack("B", 0)

        frame = double_sync + b"\x00\x00" + payload_length + frame_id + flags + data
        print("frame without chksum defined: ", frame)

        chksum = self.checksum(frame)
        print("chksum: ", chksum)
        print("chksum hex: ", hex(chksum))
        checksum = struct.pack("!H", chksum)

        frame = double_sync + checksum + payload_length + frame_id + flags + data
        print("frame with chksum defined", frame)

        return frame

    def encode_ack(self, id: int):
        double_sync = struct.pack("!II", self.sync, self.sync)
        payload_length = struct.pack("!H", 0)
        frame_id = struct.pack("B", id)
        flags = struct.pack("B", 0x80)

        #                        checksum improvisado
        frame = double_sync + b"\x00\x00" + payload_length + frame_id + flags
        print(frame)

        return frame

    def decode(self, packet: bytes):
        pass
