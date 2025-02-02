import hashlib
import logging
import socket
import sys

from protocol import DCCNET

MAX_DATA_LENGTH = 4096

dccnet = DCCNET()


def communicate(conn, gas):
    send_id = 0
    last_id = 1
    last_chksum = -1

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

        if not dccnet.is_acceptable_frame(
            recv["checksum"], recv["length"], recv["id"], recv["flags"], recv["data"]
        ):
            continue

        if dccnet.is_ack_frame(recv["flags"]) and send_id == recv["id"]:
            logging.info("ACK for authentication received")
            authenticated = True
            send_id = (send_id + 1) % 2
        if dccnet.is_reset_frame(recv["flags"]):
            logging.info("received an RESET frame during authentication")
            logging.info(f"content: {recv['data'].decode()}")
            logging.info("terminating...")
            conn.close()
            return

    logging.info("authenticated, now sending hashs")

    while not all_data_received:
        try:
            # recebe um frame de dados
            recv = dccnet.receive_frame(conn)
            logging.info(f"frame received: {recv}")
        except socket.timeout:
            continue

        if not dccnet.is_acceptable_frame(
            recv["checksum"], recv["length"], recv["id"], recv["flags"], recv["data"]
        ):
            continue

        if dccnet.is_reset_frame(recv["flags"]):
            logging.info("received an RESET frame")
            logging.info(f"content: {recv['data'].decode()}")
            logging.info("terminating...")
            conn.close()
            return

        # quadro duplicado, reenviando o ACK
        if recv["id"] == last_id and recv["checksum"] == last_chksum:
            logging.info("duplicate, resending ack")
            ack, _ = dccnet.encode_ack(last_id)
            dccnet.send_frame(conn, ack)
            continue

        last_id = recv["id"]
        last_chksum = recv["checksum"]

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
        to_send = []
        # mensagem incompleta
        if message[-1] != "\n":
            acc += message
        else:
            # o fim de uma mensagem começada acabou de ser recebido
            if acc != "":
                acc += message[0:-1]
                to_send.append(acc)
                acc = ""

            else:
                # mensagem comum recebida
                # itera pelas possíveis mensagens, envia e aguarda
                # confirmação de cada uma delas
                for m in message.split("\n"):
                    if m != "":
                        to_send.append(m)

        for message in to_send:
            hash = hashlib.md5(message.encode())
            frame, _ = dccnet.encode((hash.hexdigest() + "\n").encode(), send_id, 0x00)

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
                    ack_received = True
                    send_id = (send_id + 1) % 2
                elif dccnet.is_reset_frame(recv["flags"]):
                    logging.info("received an RESET frame")
                    logging.info(f"content: {recv['data'].decode()}")
                    logging.info("terminating...")
                    conn.close()
                    return

    conn.close()


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


if __name__ == "__main__":
    main()
