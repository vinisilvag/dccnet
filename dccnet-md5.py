import hashlib
import logging
import socket
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096

dccnet = DCCNET()


def communicate(conn, gas):
    send_id = 0

    authenticated = False
    all_data_received = False

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
            # recebe um frame de dados
            recv = dccnet.receive_frame(conn)
            logging.info(f"frame received: {recv}")
        except socket.timeout:
            continue

        if dccnet.is_reset_frame(recv["flags"]):
            logging.info("received an RESET frame")
            logging.info("content:", recv["data"].decode())
            logging.info("terminating...")
            sys.exit(1)

        # confirma o frame de dados
        logging.info("data frame, sending ack")
        ack, _ = dccnet.encode_ack(recv["id"])
        dccnet.send_frame(conn, ack)
        logging.info(f"ACK sent: {ack}")

        # END flag setada, finaliza o recebimento/envio de dados
        if dccnet.is_end_frame(recv["flags"]):
            all_data_received = True
            logging.info("frame with END flag received, ending...")
            continue

        message = recv["data"].decode()
        # mensagem incompleta
        if message[-1] != "\n":
            acc += message
        else:
            # o fim de uma mensagem começada acabou de ser recebido
            if acc != "":
                acc += message[0:-1]
                hash = hashlib.md5(acc.encode())
                frame, _ = dccnet.encode(
                    (hash.hexdigest() + "\n").encode(), send_id, 0x00
                )
                acc = ""

                ack_received = False
                while not ack_received:
                    dccnet.send_frame(conn, frame)
                    logging.info(f"frame sent: {frame}")
                    try:
                        recv = dccnet.receive_frame(conn)
                        logging.info(f"frame received: {recv}")
                    except socket.timeout:
                        continue

                    if dccnet.is_ack_frame(recv["flags"]):
                        ack_received = True
                        send_id = (send_id + 1) % 2
                    elif dccnet.is_reset_frame(recv["flags"]):
                        logging.info("received an RESET frame")
                        logging.info("content:", recv["data"].decode())
                        logging.info("terminating...")
                        sys.exit(1)
            else:  # mensagem comum recebida
                # itera pelas possíveis mensagens, envia e aguarda
                # confirmação de cada uma delas
                for m in message.split("\n"):
                    if m != "":
                        hash = hashlib.md5(m.encode())
                        frame, _ = dccnet.encode(
                            (hash.hexdigest() + "\n").encode(), send_id, 0x00
                        )

                        ack_received = False
                        while not ack_received:
                            dccnet.send_frame(conn, frame)
                            logging.info(f"frame sent: {frame}")
                            try:
                                recv = dccnet.receive_frame(conn)
                                logging.info(f"frame received: {recv}")
                            except socket.timeout:
                                continue

                            if dccnet.is_ack_frame(recv["flags"]):
                                ack_received = True
                                send_id = (send_id + 1) % 2
                            elif dccnet.is_reset_frame(recv["flags"]):
                                logging.info("received an RESET frame")
                                logging.info("content:", recv["data"].decode())
                                logging.info("terminating...")
                                sys.exit(1)


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
