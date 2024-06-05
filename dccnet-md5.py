import sys


def main():
    if len(sys.argv) != 3:
        print(
            "Invalid argument number.",
            "\nCorrect usage is: python3 dccnet-md5.py -c <IP>:<PORT>",
        )
        sys.exit(1)

    flag = sys.argv[1]
    match flag:
        case "-c":
            ip, port = sys.argv[2].split(":")
        case _:
            print("Invalid flag.", "\nThe only flag currently available is: -c")
            sys.exit(1)


if __name__ == "__main__":
    main()
