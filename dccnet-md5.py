import socket
import struct
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096
GAS = "2021421869  :44:87407f792f59b7dde2bf51a0ae7216cf8c246a7169b52ac336bbf166938d91a1+2020054250  :44:50527ec32fc4c6fd5493533c67ce42f5fcad7bb59723976ff54acc6ae84385b8+2021421940  :44:a70a80b0528f580bb6c0a94ae37e3d8efdfb7adb9f939f3af675e9ea69694db4+f16d50fda86436470ba832a3f63525650dbd1fe021e867069f35ef4073d1b637\n"

dccnet = DCCNET()


def is_ack_frame(length_recv, flags_recv):
    return length_recv == 0 and flags_recv & 0x80


def is_reset_frame(id_recv, flags_recv):
    return hex(id_recv) == hex(0xFFFF) and flags_recv & 0x20

def receive(s):
    sync_pattern = b'\xDC\xC0\x23\xC2'
    sync_length = 4  # 4 bytes

    def read_next_byte():
        byte = s.recv(1)
        if not byte:
            return None
        return byte

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
        sync2 = window[sync_length:sync_length*2]

        print("\n[SYNCHRONIZING] Reading sync prefix")
        print(f"sync1: {sync1.hex()}, sync2: {sync2.hex()}")

        if sync1 == sync_pattern and sync2 == sync_pattern:
            print("[SYNCHRONIZING] Valid sync\n")
            break
        else:
            print("sync diff")

            # Deslizar a janela para a esquerda em 1 byte
            window.pop(0)

            # Ler o próximo byte
            byte = read_next_byte()
            if byte is None:
                return None
            window.extend(byte)

    # def receive(s):
    #     sync1 = s.recv(4)
    #     sync2 = s.recv(4)
    #     sync1 = hex(struct.unpack("!I", sync1)[0])
    #     sync2 = hex(struct.unpack("!I", sync2)[0])

    #     print("\n[SYNCHRONIZING] Reading sync prefix")
    #     print(sync1)
    #     print(sync2)

    #     while sync1 != hex(0xDCC023C2) and sync2 != hex(0xDCC023C2):
    #         print("sync diff")
    #         sys.exit(1)

    #     print("[SYNCHRONIZING] Valid sync\n")

    checksum = struct.unpack("!H", s.recv(2))[0]
    length = struct.unpack("!H", s.recv(2))[0]
    id = struct.unpack("!H", s.recv(2))[0]
    flags = struct.unpack("!B", s.recv(1))[0]
    data = s.recv(length)

    print("[RECEIVED] packet content:")
    print("checksum:", hex(checksum))
    print("length:", length)
    print("id:", id)
    print("flags:", hex(flags), end="\n\n")

    return checksum, length, id, flags, data


def start_client(ip: str, port: int) -> None:
    id = 0

    is_authenticated = False
    all_data_received = False
    last_frame_sent = None

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))
        # s.settimeout(1)

        while not is_authenticated:
            frame, _ = dccnet.encode(GAS.encode(), id, 0x00)
            s.send(frame)
            last_frame_sent = frame

            try:
                (checksum_recv, length_recv, id_recv, flags_recv, data_recv) = receive(
                    s
                )
                if is_ack_frame(length_recv, flags_recv):
                    print("received an ACK for authentication")
                    is_authenticated = True
                    id = (id + 1) % 2
                elif is_reset_frame(id_recv, flags_recv):
                    print("received an RESET frame")
                    print("content:", data_recv.decode())
                    print("terminating...")
                    sys.exit(1)
                else:
                    print("received a data packet")
                    print("content:", data_recv.decode())
            except socket.timeout:
                s.send(frame)
                last_frame_sent = frame

        while not all_data_received:
            try:
                (checksum_recv, length_recv, id_recv, flags_recv, data_recv) = receive(
                    s
                )
                if is_ack_frame(length_recv, flags_recv):
                    print("received an ACK for data")
                    id = (id + 1) % 2
                elif is_reset_frame(id_recv, flags_recv):
                    print("received an RESET frame")
                    print("content:", data_recv.decode())
                    print("terminating...")
                    sys.exit(1)
                else:
                    print("received a data packet")
                    print("content:", data_recv)

                    # check stuff
                    # send MD5 message
            except socket.timeout:
                if frame is not None:
                    s.send(last_frame_sent)

            break


def main():
    if len(sys.argv) != 2:
        print(
            "Invalid argument number.",
            "\nCorrect usage is: python3 dccnet-md5.py -c <IP>:<PORT>",
        )
        sys.exit(1)

    ip, port = sys.argv[1].split(":")
    port = int(port)
    start_client(ip, port)


if __name__ == "__main__":
    main()
