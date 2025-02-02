import logging
import socket
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096
# MAX_DATA_LENGTH = 2
dccnet = DCCNET()


def setup_server(port: int, input_path: str, output_path: str) -> None:
    send_id = 0
    last_id = 1
    last_chksum = -1

    input_file = open(input_path, "rb")
    output_file = open(output_path, "wb")

    all_data_received = False
    all_data_sent = False

    payload = input_file.read(MAX_DATA_LENGTH)
    next_payload = input_file.read(MAX_DATA_LENGTH)

    if socket.has_dualstack_ipv6():
        s = socket.create_server(
            ("", port), backlog=1, family=socket.AF_INET6, dualstack_ipv6=True
        )
    else:
        s = socket.create_server(("", port), backlog=1)

    socket_info = s.getsockname()
    logging.info(f"server listening on ({socket_info[0]}):({socket_info[1]})")
    s.listen()

    conn, addr = s.accept()
    s.settimeout(1)
    logging.info(f"connected with {addr}")

    while (not all_data_sent) or (not all_data_received):
        if not all_data_received:
            try:
                recv = dccnet.receive_frame(conn)
                logging.info(f"frame received: {recv}")

                if not dccnet.is_acceptable_frame(
                    recv["checksum"],
                    recv["length"],
                    recv["id"],
                    recv["flags"],
                    recv["data"],
                ):
                    logging.info("not acceptable packet, discarting")
                    pass
                elif dccnet.is_reset_frame(recv["flags"]):
                    # reset frame
                    logging.info("received an RESET frame")
                    logging.info(f"content: {recv['data'].decode()}")
                    logging.info("terminating...")
                    sys.exit(1)
                elif dccnet.is_ack_frame(recv["flags"]):
                    logging.info("duplicate ack, continuing...")
                    pass
                else:
                    if recv["id"] == last_id and recv["checksum"] == last_chksum:
                        # quadro repetido
                        logging.info("duplicate, resending ack")
                        ack, _ = dccnet.encode_ack(last_id)
                        dccnet.send_frame(conn, ack)
                    else:
                        # quadro de dados
                        last_id = recv["id"]
                        last_chksum = recv["checksum"]

                        logging.info("data frame, writing data")
                        output_file.write(recv["data"])

                        if dccnet.is_end_frame(recv["flags"]):
                            all_data_received = True
                            output_file.close()
                            logging.info("frame with END flag received")

                        logging.info("sending ACK")
                        ack, _ = dccnet.encode_ack(recv["id"])
                        dccnet.send_frame(conn, ack)
            except socket.timeout:
                pass

        if not all_data_sent:
            if payload == b"":
                if not all_data_sent:
                    all_data_sent = True
                    logging.info("all data sent")
            else:
                flags = 0x00
                if next_payload == b"":
                    flags |= 0x40
                    logging.info("last frame is about to be sent")

                frame, _ = dccnet.encode(payload, send_id, flags)

                ack_received = False
                while not ack_received:
                    dccnet.send_frame(conn, frame)
                    logging.info(f"frame sent: {frame}")

                    try:
                        recv = dccnet.receive_frame(conn)
                        logging.info(f"frame received: {recv}")
                    except socket.timeout:
                        continue

                    if not dccnet.is_acceptable_frame(
                        recv["checksum"],
                        recv["length"],
                        recv["id"],
                        recv["flags"],
                        recv["data"],
                    ):
                        continue

                    if dccnet.is_ack_frame(recv["flags"]) and send_id == recv["id"]:
                        if recv["id"] == send_id:
                            logging.info("ACK frame")
                            send_id = (send_id + 1) % 2
                            payload = next_payload
                            next_payload = input_file.read(MAX_DATA_LENGTH)
                            ack_received = True
                        elif recv["id"] == last_id:
                            continue
                    elif dccnet.is_reset_frame(recv["flags"]):
                        logging.info("received an RESET frame")
                        logging.info(f"content: {recv['data'].decode()}")
                        logging.info("terminating...")
                        sys.exit(1)
                    else:
                        if recv["id"] == last_id and recv["checksum"] == last_chksum:
                            # quadro repetido
                            logging.info("duplicate, resending ack")
                            ack, _ = dccnet.encode_ack(last_id)
                            dccnet.send_frame(conn, ack)
                        else:
                            # quadro de dados
                            last_id = recv["id"]
                            last_chksum = recv["checksum"]

                            logging.info("data frame, writing data")
                            output_file.write(recv["data"])

                            if dccnet.is_end_frame(recv["flags"]):
                                all_data_received = True
                                output_file.close()
                                logging.info("frame with END flag received")

                            logging.info("sending ACK")
                            ack, _ = dccnet.encode_ack(recv["id"])
                            dccnet.send_frame(conn, ack)

    logging.info("closing input file")
    input_file.close()

    logging.info("server closing connection")
    conn.close()
    s.close()


def setup_client(ip: str, port: int, input_path: str, output_path: str) -> None:
    send_id = 0
    last_id = 1
    last_chksum = -1

    input_file = open(input_path, "rb")
    output_file = open(output_path, "wb")

    all_data_received = False
    all_data_sent = False

    payload = input_file.read(MAX_DATA_LENGTH)
    next_payload = input_file.read(MAX_DATA_LENGTH)

    connection = (ip, port)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(connection)
    s.settimeout(1)

    while (not all_data_sent) or (not all_data_received):
        if not all_data_received:
            try:
                recv = dccnet.receive_frame(s)
                logging.info(f"frame received: {recv}")

                if not dccnet.is_acceptable_frame(
                    recv["checksum"],
                    recv["length"],
                    recv["id"],
                    recv["flags"],
                    recv["data"],
                ):
                    logging.info("not acceptable packet, discarting")
                    pass
                elif dccnet.is_reset_frame(recv["flags"]):
                    # reset frame
                    logging.info("received an RESET frame")
                    logging.info(f"content: {recv['data'].decode()}")
                    logging.info("terminating...")
                    sys.exit(1)
                elif dccnet.is_ack_frame(recv["flags"]):
                    logging.info("duplicate ack, continuing...")
                    pass
                else:
                    if recv["id"] == last_id and recv["checksum"] == last_chksum:
                        # quadro repetido
                        logging.info("duplicate, resending ack")
                        ack, _ = dccnet.encode_ack(last_id)
                        dccnet.send_frame(s, ack)
                    else:
                        # quadro de dados
                        last_id = recv["id"]
                        last_chksum = recv["checksum"]

                        logging.info("data frame, writing data")
                        output_file.write(recv["data"])

                        if dccnet.is_end_frame(recv["flags"]):
                            all_data_received = True
                            output_file.close()
                            logging.info("frame with END flag received")

                        logging.info("sending ACK")
                        ack, _ = dccnet.encode_ack(recv["id"])
                        dccnet.send_frame(s, ack)
            except socket.timeout:
                pass

        if not all_data_sent:
            if payload == b"":
                if not all_data_sent:
                    all_data_sent = True
                    logging.info("all data sent")
            else:
                flags = 0x00
                if next_payload == b"":
                    flags |= 0x40
                    logging.info("last frame is about to be sent")

                frame, _ = dccnet.encode(payload, send_id, flags)

                ack_received = False
                while not ack_received:
                    dccnet.send_frame(s, frame)
                    logging.info(f"frame sent: {frame}")

                    try:
                        recv = dccnet.receive_frame(s)
                        logging.info(f"frame received: {recv}")
                    except socket.timeout:
                        continue

                    if not dccnet.is_acceptable_frame(
                        recv["checksum"],
                        recv["length"],
                        recv["id"],
                        recv["flags"],
                        recv["data"],
                    ):
                        continue

                    if dccnet.is_ack_frame(recv["flags"]) and send_id == recv["id"]:
                        if recv["id"] == send_id:
                            logging.info("ACK frame")
                            send_id = (send_id + 1) % 2
                            payload = next_payload
                            next_payload = input_file.read(MAX_DATA_LENGTH)
                            ack_received = True
                        elif recv["id"] == last_id:
                            continue
                    elif dccnet.is_reset_frame(recv["flags"]):
                        logging.info("received an RESET frame")
                        logging.info(f"content: {recv['data'].decode()}")
                        logging.info("terminating...")
                        sys.exit(1)
                    else:
                        if recv["id"] == last_id and recv["checksum"] == last_chksum:
                            # quadro repetido
                            logging.info("duplicate, resending ack")
                            ack, _ = dccnet.encode_ack(last_id)
                            dccnet.send_frame(s, ack)
                        else:
                            # quadro de dados
                            last_id = recv["id"]
                            last_chksum = recv["checksum"]

                            logging.info("data frame, writing data")
                            output_file.write(recv["data"])

                            if dccnet.is_end_frame(recv["flags"]):
                                all_data_received = True
                                output_file.close()
                                logging.info("frame with END flag received")

                            logging.info("sending ACK")
                            ack, _ = dccnet.encode_ack(recv["id"])
                            dccnet.send_frame(s, ack)

    logging.info("closing input file")
    input_file.close()

    logging.info("client closing connection")
    s.close()


def main():
    if len(sys.argv) != 5:
        print(
            "Invalid argument number.",
            "\nCorrect usage is:",
            "\n  python3 dccnet-xfer.py -s <PORT> <INPUT> <OUTPUT>",
            "\n  python3 dccnet-xfer.py -c <IP>:<PORT> <INPUT> <OUTPUT>",
        )
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO, datefmt="%H:%M:%S", format="%(asctime)s: %(message)s"
    )

    flag = sys.argv[1]
    match flag:
        case "-c":
            ip, port = sys.argv[2].split(":")
            port = int(port)
            input = sys.argv[3]
            output = sys.argv[4]
            setup_client(ip, port, input, output)
        case "-s":
            port = int(sys.argv[2])
            input = sys.argv[3]
            output = sys.argv[4]
            setup_server(port, input, output)
        case _:
            print("Invalid flag.\nFlags currently available are: -s and -c")
            sys.exit(1)


if __name__ == "__main__":
    main()
