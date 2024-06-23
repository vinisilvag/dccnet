import socket
import struct
import sys


class DCCNET:
    def __init__(self) -> None:
        self.sync = 0xDCC023C2

    def resolve_connection(self, host, port):
        try:
            addr_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in addr_info:
                ip_address = sockaddr[0]
                if family == socket.AF_INET6:
                    return (ip_address, family)
            for family, _, _, _, sockaddr in addr_info:
                ip_address = sockaddr[0]
                if family == socket.AF_INET:
                    return (ip_address, family)
        except socket.gaierror as e:
            print("error connecting to the server:", e)
            sys.exit(1)

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

    def is_ack_frame(self, flags_recv):
        return flags_recv & 0x80

    def is_reset_frame(self, flags_recv):
        return flags_recv & 0x20

    def reconstruct_frame(self, length_recv, id_recv, flags_recv, data_recv):
        frame = struct.pack(
            f">IIHHHB{length_recv}s",
            self.sync,
            self.sync,
            0,
            length_recv,
            id_recv,
            flags_recv,
            data_recv,
        )

        chksum = self.checksum(frame)
        checksum = struct.pack("<H", chksum)

        frame = struct.pack(
            f">II2sHHB{length_recv}s",
            self.sync,
            self.sync,
            checksum,
            length_recv,
            id_recv,
            flags_recv,
            data_recv,
        )

        return frame, chksum

    def checksum_match(self, checksum_calc, checksum_recv):
        return checksum_calc == checksum_recv

    def encode(self, data: bytes, id: int, flags: int):
        frame = struct.pack(
            f">IIHHHB{len(data)}s", self.sync, self.sync, 0, len(data), id, flags, data
        )

        chksum = self.checksum(frame)
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

        return frame, chksum

    def encode_ack(self, id: int):
        frame, chksum = self.encode("".encode(), id, 0x80)
        return frame, chksum

    def send_frame(self, conn, frame):
        conn.send(frame)

    def receive_frame(self, conn):
        def read_next_byte():
            byte = conn.recv(1)
            if not byte:
                return None
            return byte

        sync_pattern = b"\xdc\xc0\x23\xc2"
        sync_length = 4  # 4 bytes

        # Inicializar a janela de 8 bytes (64 bits)
        window = bytearray()
        for _ in range(8):
            byte = read_next_byte()
            if byte is None:
                return None
            window.extend(byte)

        while True:
            # Extrair os primeiros 4 bytes e os últimos 4 bytes da janela
            sync1 = window[:sync_length]
            sync2 = window[sync_length : sync_length * 2]

            # print("\n[SYNCHRONIZING] Reading sync prefix")
            # print(f"sync1: {sync1.hex()}, sync2: {sync2.hex()}")

            if sync1 == sync_pattern and sync2 == sync_pattern:
                # print("[SYNCHRONIZING] Valid sync\n")
                break
            else:
                # print("sync diff")

                # Deslizar a janela para a esquerda em 1 byte
                window.pop(0)

                # Ler o próximo byte
                byte = read_next_byte()
                if byte is None:
                    return None
                window.extend(byte)

        checksum = struct.unpack("<H", conn.recv(2))[0]
        length = struct.unpack("!H", conn.recv(2))[0]
        id = struct.unpack("!H", conn.recv(2))[0]
        flags = struct.unpack("!B", conn.recv(1))[0]
        data = conn.recv(length)

        # print("[RECEIVED] packet content:")
        # print("checksum:", hex(checksum))
        # print("length:", length)
        # print("id:", id)
        # print("flags:", hex(flags), end="\n\n")

        return {
            "id": id,
            "flags": flags,
            "checksum": checksum,
            "length": length,
            "data": data,
        }
