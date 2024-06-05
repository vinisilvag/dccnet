import struct

from protocol import DCCNET


def main():
    protocol = DCCNET()
    frame = protocol.encode(struct.pack(">bbbb", 1, 2, 3, 4), 0)


if __name__ == "__main__":
    main()
