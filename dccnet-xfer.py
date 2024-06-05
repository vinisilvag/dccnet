import socket
import sys


def setup_server(host: str, port: int, input: str, output: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Server listening on {host}:{port}...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")


def setup_client(ip: str, port: int, input: str, output: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))


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
            host = "127.0.0.1"
            port = int(sys.argv[2])
            input = sys.argv[3]
            output = sys.argv[4]
            setup_server(host, port, input, output)

        case _:
            print("Invalid flag.\nFlags currently available are: -s -c")
            sys.exit(1)


if __name__ == "__main__":
    main()
