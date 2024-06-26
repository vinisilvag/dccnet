import struct
import time
from protocol import DCCNET
from multiprocessing import Process
import importlib  
dccnet_xfer = importlib.import_module("dccnet-xfer")

GAS = "2021421869  :44:87407f792f59b7dde2bf51a0ae7216cf8c246a7169b52ac336bbf166938d91a1+2020054250  :44:50527ec32fc4c6fd5493533c67ce42f5fcad7bb59723976ff54acc6ae84385b8+2021421940  :44:a70a80b0528f580bb6c0a94ae37e3d8efdfb7adb9f939f3af675e9ea69694db4+f16d50fda86436470ba832a3f63525650dbd1fe021e867069f35ef4073d1b637\n"

dccnet = DCCNET()


def debug_checksum():
    frame, checksum = dccnet.encode(GAS.encode(), 0, 0x00)
    print("got:", hex(checksum))
    print("expected: 0xfd27")

    print()
    received = struct.unpack(">IIHHHB308s", frame)
    print(hex(received[0]), hex(received[1]))
    print(hex(received[2]))
    print(received[3])
    print(received[4])
    print(hex(received[5]))



def test_server_client():
    host="127.0.1.1"
    port=6546
    server_input="tamborzao-corki.mp3"
    server_output="lenna-received.png"
    client_input="lenna.png"
    client_output="tamborzao-corki-received.mp3"

    def start_server():
        dccnet_xfer.setup_server(host, port, server_input, server_output)

    def start_client():
        time.sleep(1)  # Como são executados em paralelo, isso garante que o cliente inicie depois do servidor
        dccnet_xfer.setup_client(host, port, client_input, client_output)

    
    p1 = Process(target=start_server)
    p2 = Process(target=start_client)

    print("starting server")
    p1.start()
    
    print("starting client")
    print("Wait . . . ")
    p2.start()

    p1.join()
    p2.join()

    

def main():
    # frame = dccnet.encode(struct.pack(">bbbb", 1, 2, 3, 4), 0, 0)
    #debug_checksum()
    test_server_client()


if __name__ == "__main__":
    main()
