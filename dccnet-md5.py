import hashlib
import logging
import socket
import struct
import sys
import threading

from protocol import DCCNET

MAX_DATA_LENGTH = 4096

dccnet = DCCNET()


def is_ack_frame(length_recv, flags_recv):
    return length_recv == 0 and flags_recv & 0x80


def is_reset_frame(id_recv, flags_recv):
    return hex(id_recv) == hex(0xFFFF) and flags_recv & 0x20


def reconstruct_frame(length_recv, id_recv, flags_recv, data_recv):
    frame = struct.pack(
        f">IIHHHB{length_recv}s",
        dccnet.sync,
        dccnet.sync,
        0,
        length_recv,
        id_recv,
        flags_recv,
        data_recv,
    )
    # print("frame without chksum defined: ", frame)

    chksum = dccnet.checksum(frame)
    # print("chksum: ", chksum)
    # print("chksum hex: ", hex(chksum))
    checksum = struct.pack("<H", chksum)

    frame = struct.pack(
        f">II2sHHB{length_recv}s",
        dccnet.sync,
        dccnet.sync,
        checksum,
        length_recv,
        id_recv,
        flags_recv,
        data_recv,
    )
    # print("frame with chksum defined", frame)

    return frame, chksum


def checksum_match(checksum_calc, checksum_recv):
    return checksum_calc == checksum_recv


def receive(conn):
    sync1 = conn.recv(4)
    sync2 = conn.recv(4)
    sync1 = hex(struct.unpack("!I", sync1)[0])
    sync2 = hex(struct.unpack("!I", sync2)[0])

    # print("\n[SYNCHRONIZING]")
    # print("reading sync prefix")

    while sync1 != hex(0xDCC023C2) and sync2 != hex(0xDCC023C2):
        print("sync diff")
        sys.exit(1)

    # print("\n[SYNCHRONIZING]")
    # print("valid sync, reading frame content")

    checksum = struct.unpack("<H", conn.recv(2))[0]
    length = struct.unpack("!H", conn.recv(2))[0]
    id = struct.unpack("!H", conn.recv(2))[0]
    flags = struct.unpack("!B", conn.recv(1))[0]
    data = conn.recv(length)

    return {
        "id": id,
        "flags": hex(flags),
        "length": length,
        "checksum": hex(checksum),
        "data": data,
    }


def start_client(ip: str, port: int, gas: str) -> None:
    id = 0

    is_authenticated = False
    all_data_received = False
    last_frame_sent = None

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))
        s.settimeout(1)

        print("\n[AUTH]")
        print("sending authentication frame")
        frame, _ = dccnet.encode((gas + "\n").encode(), id, 0x00)
        s.send(frame)
        last_frame_sent = frame

        while not is_authenticated:
            try:
                (
                    checksum_recv,
                    length_recv,
                    id_recv,
                    flags_recv,
                    data_recv,
                ) = receive(s)
                if is_ack_frame(length_recv, flags_recv):
                    print("\n[AUTH]")
                    print("received an ACK")
                    is_authenticated = True
                elif is_reset_frame(id_recv, flags_recv):
                    print("\n[AUTH]")
                    print("received an RESET frame")
                    print("content:", data_recv.decode())
                    print("terminating...")
                    sys.exit(1)
            except socket.timeout:
                print("[AUTH]")
                print("retransmiting the authentication frame")
                s.send(last_frame_sent)

        print("\n[AUTH]")
        print("authentication finished: correctly authenticated")

        while not all_data_received:
            try:
                (
                    checksum_recv,
                    length_recv,
                    id_recv,
                    flags_recv,
                    data_recv,
                ) = receive(s)
                if is_ack_frame(length_recv, flags_recv):
                    print("\n[DATA]")
                    print("received an ACK")
                    id = (id + 1) % 2
                elif is_reset_frame(id_recv, flags_recv):
                    print("\n[DATA]")
                    print("received an RESET frame")
                    print("content:", data_recv.decode())
                    print("terminating...")
                    sys.exit(1)
                else:
                    print("\n[DATA]")

                    frame_calc, checksum_calc = reconstruct_frame(
                        length_recv, id_recv, flags_recv, data_recv
                    )
                    if checksum_match(checksum_calc, checksum_recv):
                        print("checksum match")
                        print("frame with data received, sending ack")
                        ack, _ = dccnet.encode_ack(id_recv)
                        s.send(ack)
                        last_frame_sent = ack
                        print(f"ack sended with id {id_recv}")

                    # print("sending hashed message")
                    # message = data_recv.decode().split("\n")[0]
                    # md5 = hashlib.md5(message.encode())
                    # encode = md5.hexdigest().encode()
                    # frame, _ = dccnet.encode(encode, id, 0x00)
                    # s.send(frame)
                    # last_frame_sent = frame
                    # print(f"hash message sended with id {id + 1}")
            except socket.timeout:
                print("timeout, resending last frame")
                s.send(last_frame_sent)

            # while not all_data_received:
            #     try:
            #         (
            #             checksum_recv,
            #             length_recv,
            #             id_recv,
            #             flags_recv,
            #             data_recv,
            #         ) = receive(s)
            #         if is_ack_frame(length_recv, flags_recv):
            #             print("received an ACK for data")
            #             id = (id + 1) % 2
            #         elif is_reset_frame(id_recv, flags_recv):
            #             print("received an RESET frame")
            #             print("content:", data_recv.decode())
            #             print("terminating...")
            #             sys.exit(1)
            #         else:
            #             print("received a data packet")
            #             print("content:", data_recv)
            #             frame_calc, checksum_calc = reconstruct_frame(
            #                 length_recv, id_recv, flags_recv, data_recv
            #             )
            #             if checksum_match(checksum_calc, checksum_recv):
            #                 print("checksum match!")
            #                 print("ids - receive:", id_recv, "curr: ", id)
            #                 print("send ack")
            #                 frame, _ = dccnet.encode_ack(id)
            #                 s.send(frame)
            #                 last_frame_sent = frame
            #
            #                 id = (id + 1) % 2
            #
            #                 message = data_recv.decode().split("\n")[0]
            #                 md5 = hashlib.md5(message.encode())
            #                 encode = md5.hexdigest().encode()
            #                 frame, _ = dccnet.encode(encode, id, 0x00)
            #                 s.send(frame)
            #                 last_frame_sent = frame
            #
            #     except socket.timeout:
            #         s.send(last_frame_sent)


def recv_worker(conn):
    logging.info("receiver thread started")
    finished = False

    # while not finished:
    #     try:
    #         recv = receive(conn)
    #         print(f"received frame: {recv}")
    #         if is_ack_frame(recv["length"], recv["flags"]):
    #             print("ack received")
    #         elif is_reset_frame(recv["id"], recv["flags"]):
    #             print("received an RESET frame")
    #             print("content:", recv["data"].decode())
    #             print("terminating...")
    #             sys.exit(1)
    #         else:
    #             print("alguma coisa")
    #     except socket.timeout:
    #         print("timeout")


def send_worker(conn, gas):
    logging.info("sender thread started")

    # authentication frame
    gas += "\n"
    frame, _ = dccnet.encode(gas.encode(), 0, 0x00)
    conn.send(frame)
    print("sent authentication frame")

    # ack authentication
    recv = receive(conn)
    print(f"received frame: {recv}")

    # frame data
    recv = receive(conn)
    print(f"received frame: {recv}")

    # ack frame data
    frame, _ = dccnet.encode_ack(0)
    conn.send(frame)
    print("ack sended")

    recv = receive(conn)
    print(f"received frame: {recv}")

    # message = recv["data"].decode().split("\n")[0]
    # print(message)
    # md5 = hashlib.md5(message.encode())
    # encode = md5.hexdigest()
    # print(encode)
    # frame, _ = dccnet.encode(encode.encode(), 1, 0x00)
    # conn.send(frame)
    #
    # frame, _ = dccnet.encode("\n".encode(), 1, 0x00)
    # conn.send(frame)

    # recv = receive(conn)
    # print(f"received frame: {recv}")
    # recv = receive(conn)
    # print(f"received frame: {recv}")

    # recv = receive(conn)
    # print(f"received frame: {recv}")

    # recv = receive(conn)
    # print(f"received frame: {recv}")
    # while True:
    #     try:
    #         recv = receive(conn)
    #         print(f"received frame: {recv}")
    #         break
    #     except socket.timeout:
    #         frame, _ = dccnet.encode_ack(1)
    #         conn.send(frame)


def main():
    if len(sys.argv) != 3:
        print(
            "Invalid argument number.",
            "\nCorrect usage is: python3 dccnet-md5.py -c <IP>:<PORT> <GAS>",
        )
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO, datefmt="%H:%M:%S", format="%(asctime)s: %(message)s"
    )

    ip, port = sys.argv[1].split(":")
    gas = sys.argv[2]
    port = int(port)

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((ip, port))
    conn.settimeout(1)

    logging.info(f"connected with server {(ip, port)}")

    sender = threading.Thread(target=send_worker, args=(conn, gas))
    receiver = threading.Thread(target=recv_worker, args=(conn,))

    sender.start()
    receiver.start()
    sender.join()
    receiver.join()

    conn.close()

    # start_client(ip, port, gas)


if __name__ == "__main__":
    main()
