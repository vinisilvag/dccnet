import socket
import struct
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096
dccnet = DCCNET()


def is_ack_frame(id, id_recv, length, flags):
    return id == id_recv and length == 0 and flags & 0x80


def receive_frame(s):
    sync1 = s.recv(4)
    sync2 = s.recv(4)
    sync1 = hex(struct.unpack("!I", sync1)[0])
    sync2 = hex(struct.unpack("!I", sync2)[0])

    print(sync1)
    print(sync2)

    while sync1 != hex(0xDCC023C2) and sync2 != hex(0xDCC023C2):
        print("sync diff")
        sys.exit(1)

    print("valid sync")

    checksum = struct.unpack("!H", s.recv(2))[0]
    length = struct.unpack("!H", s.recv(2))[0]
    id = struct.unpack("!H", s.recv(2))[0]
    flags = struct.unpack("!B", s.recv(1))[0]
    data = s.recv(length)

    print("checksum:", hex(checksum))
    print("length:", length)
    print("id:", id)
    print("flags:", hex(flags))
    print("data:", data)

    # frame = sync1 + sync2 + checksum + length + id + flags + data

    return checksum, length, id, flags, data


def setup_server(host: str, port: int, input: str, output: str) -> None:
    id = 0
    input_file = open(input, "r")

    payload = input_file.read(MAX_DATA_LENGTH)
    next_payload = input_file.read(MAX_DATA_LENGTH)

    all_data_sent = False
    all_data_received = False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Server listening on {host}:{port}...")

        conn, addr = s.accept()
        with conn:
            # s.settimeout(1)
            print(f"Connected by {addr}")

            try:
                while (not all_data_sent) or (not all_data_received):
                    break
            finally:
                input_file.close()


def setup_client(ip: str, port: int, input: str, output: str) -> None:
    id = 0
    input_file = open(input, "r")

    payload = input_file.read(MAX_DATA_LENGTH)
    next_payload = input_file.read(MAX_DATA_LENGTH)

    all_data_sent = False
    all_data_received = False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))
        # s.settimeout(1)

        try:
            while (not all_data_sent) or (not all_data_received):
                flags_send = 0x00
                if next_payload == "":
                    flags_send |= 0x40

                if payload == "":
                    all_data_sent = True
                else:
                    frame, chksum_send = dccnet.encode(payload.encode(), id, flags_send)
                    s.send(frame)

                try:
                    (
                        chksum_recv,
                        length_recv,
                        id_recv,
                        flags_recv,
                        data_recv,
                    ) = receive_frame(s)
                except socket.timeout:
                    frame, chksum_send = dccnet.encode(payload.encode(), id, flags_send)
                    s.send(frame)

                if is_ack_frame(id, id_recv, length_recv, flags_recv):
                    payload = next_payload
                    next_payload = input_file.read(MAX_DATA_LENGTH)
                    id = (id + 1) % 2
                else:
                    print("received a data frame")
                    print("data frame:", data_recv)

                break
        finally:
            input_file.close()


def main():
    if len(sys.argv) != 5:
        print(
            "Invalid argument number.",
            "\nCorrect usage is:",
            "\n  python3 dccnet-xfer.py -s <PORT> <INPUT> <OUTPUT>",
            "\n  python3 dccnet-xfer.py -c <IP>:<PORT> <INPUT> <OUTPUT>",
        )
        sys.exit(1)

    flag = sys.argv[1]
    match flag:
        case "-c":
            ip, port = sys.argv[2].split(":")
            port = int(port)
            input = sys.argv[3]
            output = sys.argv[4]
            setup_client(ip, port, input, output)
        case "-s":
            host = socket.gethostbyname(socket.getfqdn())
            port = int(sys.argv[2])
            input = sys.argv[3]
            output = sys.argv[4]
            setup_server(host, port, input, output)
        case _:
            print("Invalid flag.\nFlags currently available are: -s and -c")
            sys.exit(1)


if __name__ == "__main__":
    main()
