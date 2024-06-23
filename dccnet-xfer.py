import logging
import socket
import struct
import sys

from protocol import DCCNET

# MAX_DATA_LENGTH = 4096
MAX_DATA_LENGTH = 2
dccnet = DCCNET()


def setup_server(host: str, port: int, input: str, output: str) -> None:
    send_id = 0
    last_id = 1
    last_chksum = None

    input_file = open(input, "r")
    output_file = open(output, "w")

    all_data_received = False
    all_data_sent = False

    payload = input_file.read(MAX_DATA_LENGTH)
    next_payload = input_file.read(MAX_DATA_LENGTH)

    connection = (host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(connection)
        s.listen()
        logging.info(f"server listening on {host}:{port}")

        conn, addr = s.accept()
        with conn:
            conn.settimeout(1)
            logging.info(f"connected with {addr}")

            while not all_data_sent or not all_data_received:
                flags = 0x00
                if next_payload == "":
                    flags |= 0x40

                if payload == "":
                    if not all_data_sent:
                        all_data_sent = True
                        logging.info("all data sent")
                else:
                    frame, _ = dccnet.encode(payload.encode(), send_id, flags)
                    dccnet.send_frame(conn, frame)
                    logging.info(f"frame sent: {frame}")

                try:
                    recv = dccnet.receive_frame(conn)
                except socket.timeout:
                    continue

                logging.info(f"frame received: {recv}")
                if dccnet.is_ack_frame(recv["flags"]):
                    logging.info("received an ACK frame")
                    if recv["id"] == send_id:
                        payload = next_payload
                        next_payload = input_file.read(MAX_DATA_LENGTH)
                        send_id = (send_id + 1) % 2
                else:
                    # quadro duplicado
                    if recv["checksum"] == last_chksum and recv["id"] == last_id:
                        logging.info("duplicate frame, resending ack")
                        ack, _ = dccnet.encode_ack(last_id)
                        dccnet.send_frame(conn, ack)
                    else:
                        # checksum diferente mas id igual (erro)
                        if recv["checksum"] != last_chksum and recv["id"] == last_id:
                            continue

                        last_id = recv["id"]
                        last_chksum = recv["checksum"]

                        output_file.write(recv["data"].decode())
                        if recv["flags"] & 0x40:
                            all_data_received = True
                            logging.info("all data received")
                            logging.info("closing output file")
                            output_file.close()

                        logging.info("nice frame, sending ack")
                        ack, _ = dccnet.encode_ack(recv["id"])
                        dccnet.send_frame(conn, ack)

    logging.info("closing input file")
    input_file.close()


def setup_client(ip: str, port: int, input: str, output: str) -> None:
    send_id = 0
    last_id = 1
    last_chksum = None

    input_file = open(input, "r")
    output_file = open(output, "w")

    all_data_received = False
    all_data_sent = False

    payload = input_file.read(MAX_DATA_LENGTH)
    next_payload = input_file.read(MAX_DATA_LENGTH)

    connection = (ip, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(connection)
        s.settimeout(1)

        while not all_data_sent or not all_data_received:
            flags = 0x00
            if next_payload == "":
                flags |= 0x40

            if payload == "":
                if not all_data_sent:
                    all_data_sent = True
                    logging.info("all data sent")
            else:
                frame, chksum_send = dccnet.encode(payload.encode(), send_id, flags)
                dccnet.send_frame(s, frame)
                logging.info(f"frame sent: {frame}")

            try:
                recv = dccnet.receive_frame(s)
            except socket.timeout:
                continue

            logging.info(f"frame received: {recv}")
            if dccnet.is_ack_frame(recv["flags"]):
                logging.info("received an ACK frame")
                if recv["id"] == send_id:
                    payload = next_payload
                    next_payload = input_file.read(MAX_DATA_LENGTH)
                    send_id = (send_id + 1) % 2
            else:
                # quadro duplicado
                if recv["checksum"] == last_chksum and recv["id"] == last_id:
                    logging.info("duplicate frame, resending ack")
                    ack, _ = dccnet.encode_ack(last_id)
                    dccnet.send_frame(s, ack)
                else:
                    # checksum diferente mas id igual (erro)
                    if recv["checksum"] != last_chksum and recv["id"] == last_id:
                        continue

                    last_id = recv["id"]
                    last_chksum = recv["checksum"]

                    output_file.write(recv["data"].decode())
                    if recv["flags"] & 0x40:
                        all_data_received = True
                        logging.info("all data received")
                        logging.info("closing output file")
                        output_file.close()

                    logging.info("nice frame, sending ack")
                    ack, _ = dccnet.encode_ack(recv["id"])
                    dccnet.send_frame(s, ack)

    logging.info("closing input file")
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
