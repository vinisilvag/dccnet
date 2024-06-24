import hashlib
import logging
import socket
import struct
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096

dccnet = DCCNET()


def communicate(conn, gas):
    send_id = 0
    last_id = 1
    last_chksum = None

    authenticated = False
    all_data_received = False

    last_frame = None
    acc = ""

    while not authenticated:
        auth, _ = dccnet.encode((gas + "\n").encode(), send_id, 0x00)
        dccnet.send_frame(conn, auth)
        logging.info(f"auth frame sent: {auth}")

        try:
            recv = dccnet.receive_frame(conn)
            logging.info(f"frame received: {recv}")
        except socket.timeout:
            continue

        if dccnet.is_ack_frame(recv["flags"]):
            logging.info("ACK for authentication received")
            authenticated = True
            send_id = (send_id + 1) % 2

    logging.info("authenticated, now sending hashs")

    while not all_data_received:
        try:
            # recebe um frame
            recv = dccnet.receive_frame(conn)
            logging.info(f"frame received: {recv}")
        except socket.timeout:
            continue

        # é um ACK?
        if dccnet.is_ack_frame(recv["flags"]):
            if recv["id"] == send_id:
                logging.info("ACK received")
                send_id = (send_id + 1) % 2
        elif dccnet.is_reset_frame(recv["flags"]):
            logging.info("received an RESET frame")
            logging.info("content:", recv["data"].decode())
            logging.info("terminating...")
            sys.exit(1)
        else:
            if recv["id"] == send_id:
                dccnet.send_frame(conn, last_frame)
            else:
                last_id = recv["id"]
                last_chksum = recv["checksum"]

                logging.info("data frame, sending ack")
                ack, _ = dccnet.encode_ack(recv["id"])
                dccnet.send_frame(conn, ack)
                logging.info(f"ACK sent: {ack}")

                message = recv["data"].decode()

                if message[-1] != "\n":
                    acc += message
                    # send_id = (send_id + 1) % 2
                else:
                    if acc != "":
                        acc += message[0:-1]
                        logging.info(f"ACCCCC AQUIIII {acc}")
                        # send_id = (send_id + 1) % 2
                        hash = hashlib.md5(acc.encode())
                        frame, _ = dccnet.encode(
                            (hash.hexdigest() + "\n").encode(), send_id, 0x00
                        )
                        dccnet.send_frame(conn, frame)
                        last_frame = frame
                        acc = ""
                        # send_id = (send_id + 1) % 2
                        logging.info(f"frame sent: {frame}")
                    else:
                        hash = hashlib.md5(message[0:-1].encode())
                        frame, _ = dccnet.encode(
                            (hash.hexdigest() + "\n").encode(), send_id, 0x00
                        )
                        dccnet.send_frame(conn, frame)
                        last_frame = frame
                        logging.info(f"frame sent: {frame}")

                # if messages[-1] != "":
                #     acc += messages[0]
                # else:
                #     if acc != "":
                #         acc += messages[0][0:-1]
                #         hash = hashlib.md5(acc.encode())
                #         frame, _ = dccnet.encode(
                #             (hash.hexdigest() + "\n").encode(), send_id, 0x00
                #         )
                #         dccnet.send_frame(conn, frame)
                #         last_frame = frame
                #         acc = ""
                #         logging.info(f"frame sent: {frame}")
                #     else:
                #         hash = hashlib.md5(messages[0].encode())
                #         frame, _ = dccnet.encode(
                #             (hash.hexdigest() + "\n").encode(), send_id, 0x00
                #         )
                #         dccnet.send_frame(conn, frame)
                #         last_frame = frame
                #         logging.info(f"frame sent: {frame}")

                # hash = hashlib.md5(message[0:-1].encode())
                # frame, _ = dccnet.encode(
                #     (hash.hexdigest() + "\n").encode(), send_id, 0x00
                # )
                # dccnet.send_frame(conn, frame)
                # last_frame = frame
                # logging.info(f"frame sent: {frame}")

                # try:
                #     recv = dccnet.receive_frame(conn)
                #     logging.info(f"frame received: {recv}")
                # except socket.timeout:
                #     dccnet.send_frame(conn, frame)

                #     if dccnet.is_ack_frame(recv["flags"]):
                #         if recv["id"] == send_id:  # receive the ack for the last sent frame
                #             logging.info("ACK received")
                #             send_id = (send_id + 1) % 2
                #     elif dccnet.is_reset_frame(recv["flags"]):
                #         logging.info("received an RESET frame")
                #         logging.info("content:", recv["data"].decode())
                #         logging.info("terminating...")
                #         sys.exit(1)
                #     else:
                #         if recv["checksum"] == last_chksum and recv["id"] == last_id:
                #             logging.info("duplicate frame, resending ack")
                #             ack, _ = dccnet.encode_ack(last_id)
                #             dccnet.send_frame(conn, ack)
                #         else:
                #             # checksum diferente mas id igual (erro)
                #             if recv["checksum"] != last_chksum and recv["id"] == last_id:
                #                 continue
                #
                #             last_id = recv["id"]
                #             last_chksum = recv["checksum"]
                #
                #             for message in recv["data"].decode().split("\n"):
                #                 if message != "":
                #                     logging.info(f"line received: {message}")
                #                     acc.append(message)
                #
                #             logging.info("nice frame, sending ack")
                #             ack, _ = dccnet.encode_ack(recv["id"])
                #             dccnet.send_frame(conn, ack)


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
