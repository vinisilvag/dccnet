import hashlib
import logging
import socket
import struct
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096
GAS = "2021421869  :44:87407f792f59b7dde2bf51a0ae7216cf8c246a7169b52ac336bbf166938d91a1+2020054250  :44:50527ec32fc4c6fd5493533c67ce42f5fcad7bb59723976ff54acc6ae84385b8+2021421940  :44:a70a80b0528f580bb6c0a94ae37e3d8efdfb7adb9f939f3af675e9ea69694db4+f16d50fda86436470ba832a3f63525650dbd1fe021e867069f35ef4073d1b637\n"

dccnet = DCCNET()


# def start_client(ip: str, port: int) -> None:
#     id = 0
#
#     is_authenticated = False
#     all_data_received = False
#     last_frame_sent = None
#
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.connect((ip, port))
#         # s.settimeout(1)
#
#         while not is_authenticated:
#             frame, _ = dccnet.encode(GAS.encode(), id, 0x00)
#             s.send(frame)
#             last_frame_sent = frame
#
#             try:
#                 (checksum_recv, length_recv, id_recv, flags_recv, data_recv) = receive(
#                     s
#                 )
#                 if is_ack_frame(length_recv, flags_recv):
#                     print("received an ACK for authentication")
#                     is_authenticated = True
#                     id = (id + 1) % 2
#                 elif is_reset_frame(id_recv, flags_recv):
#                     print("received an RESET frame")
#                     print("content:", data_recv.decode())
#                     print("terminating...")
#                     sys.exit(1)
#                 else:
#                     print("received a data packet")
#                     print("content:", data_recv.decode())
#             except socket.timeout:
#                 s.send(frame)
#                 last_frame_sent = frame
#
#         while not all_data_received:
#             try:
#                 (checksum_recv, length_recv, id_recv, flags_recv, data_recv) = receive(
#                     s
#                 )
#                 if is_ack_frame(length_recv, flags_recv):
#                     print("received an ACK for data")
#                     id = (id + 1) % 2
#                 elif is_reset_frame(id_recv, flags_recv):
#                     print("received an RESET frame")
#                     print("content:", data_recv.decode())
#                     print("terminating...")
#                     sys.exit(1)
#                 else:
#                     print("received a data packet")
#                     print("content:", data_recv)
#
#                     # check stuff
#                     # send MD5 message
#             except socket.timeout:
#                 if frame is not None:
#                     s.send(last_frame_sent)
#
#             break


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

    chksum = dccnet.checksum(frame)
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

    return frame, chksum


def checksum_match(checksum_calc, checksum_recv):
    return checksum_calc == checksum_recv


def dissect(frame):
    print(frame)
    print(struct.unpack("!IIHHHB", frame))

    # return {
    #     "id": id,
    #     "flags": flags,
    #     "checksum": checksum,
    #     "length": length,
    #     "data": data,
    # }


def communicate(conn, gas):
    is_authenticated = False
    end_received = False

    send_id = 0

    gas += "\n"

    while True:
        if not is_authenticated:
            logging.info("send authentication frame")
            auth_frame, _ = dccnet.encode(gas.encode(), send_id, 0x00)
            dccnet.send_frame(conn, auth_frame)
        else:
            logging.info("send hash message")

        try:
            recv = dccnet.receive_frame(conn)
            logging.info(f"frame received: {recv}")
        except socket.timeout:
            logging.info("timeout")
            continue

        if dccnet.is_ack_frame(recv["flags"]):
            logging.info("ACK received")
            if recv["id"] == send_id:
                if not is_authenticated:
                    is_authenticated = True

            send_id = (send_id + 1) % 2
        elif dccnet.is_reset_frame(recv["flags"]):
            logging.info("received an RESET frame")
            logging.info("content:", recv["data"].decode())
            sys.exit(1)
        else:
            print("other stuff")
    # auth_frame, _ = dccnet.encode(gas.encode(), id, 0x00)
    # dccnet.send_frame(conn, auth_frame)
    # logging.info("authentication frame sent")
    #
    # while not is_authenticated:
    #     try:
    #         recv = dccnet.receive_frame(conn)
    #         if dccnet.is_ack_frame(recv["length"], recv["flags"]):
    #             logging.info("ACK received for authentication")
    #             logging.info("authentication finished")
    #             is_authenticated = True
    #         elif dccnet.is_reset_frame(recv["id"], recv["flags"]):
    #             logging.info("received an RESET frame during authentication")
    #             logging.info("content:", recv["data"].decode())
    #             sys.exit(1)
    #     except socket.timeout:
    #         dccnet.send_frame(conn, auth_frame)
    #
    # logging.info("now exchanging data")
    #
    # while not end_received:
    #     try:
    #         recv = dccnet.receive_frame(conn)
    #         logging.info(f"frame received: {recv}")
    #         if dccnet.is_ack_frame(recv["length"], recv["flags"]):
    #             logging.info("ACK received for data")
    #             print("o que fazer?")
    #         elif dccnet.is_reset_frame(recv["id"], recv["flags"]):
    #             logging.info("received an RESET frame during data exchanging")
    #             logging.info(f"content: {recv['data'].decode()}")
    #             sys.exit(1)
    #         else:
    #             frame_calc, checksum_calc = reconstruct_frame(
    #                 recv["length"], recv["id"], recv["flags"], recv["data"]
    #             )
    #             if checksum_match(checksum_calc, recv["checksum"]):
    #                 logging.info("data frame received and checksum match")
    #
    #                 logging.info("sending ACK")
    #                 ack, _ = dccnet.encode_ack(id)
    #                 dccnet.send_frame(conn, ack)
    #                 logging.info("ack sent")
    #
    #                 # if recv["id"] != alguma_coisa:
    #                 # else:
    #                 # message = recv["data"].decode().split("\n")[0]
    #                 # md5 = hashlib.md5(message.encode())
    #                 # digest = md5.hexdigest()
    #                 # frame, _ = dccnet.encode(digest.encode(), 0, 0x00)
    #                 # dccnet.send_frame(conn, frame)
    #                 # logging.info(f"frame sent: {frame}")
    #     except socket.timeout:
    #         logging.info("timeout")
    #         ack, _ = dccnet.encode_ack(id)
    #         dccnet.send_frame(conn, ack)


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

    host, port = sys.argv[1].split(":")
    gas = sys.argv[2]
    port = int(port)

    (ip_address, family) = dccnet.resolve_connection(host, port)
    connection = (ip_address, port)

    conn = socket.socket(family, socket.SOCK_STREAM)
    conn.connect(connection)
    conn.settimeout(1)

    logging.info(f"connected with server {connection}")

    communicate(conn, gas)

    conn.close()


if __name__ == "__main__":
    main()
