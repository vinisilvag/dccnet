HOST=127.0.1.1
PORT=6546
SERVER_INPUT="server-input.txt"
SERVER_OUTPUT="server-output.txt"
CLIENT_INPUT="client-input.txt"
CLIENT_OUTPUT="client-output.txt"

server-send-lenna:
	python3 dccnet-xfer.py -s ${PORT} "lenna.png" "server-received-corki.mp3"
	
client-send-corki:
	python3 dccnet-xfer.py -c ${HOST}:${PORT} "tamborzao-corki.mp3" "client-received-lenna.png"

server-send-corki:
	python3 dccnet-xfer.py -s ${PORT} "tamborzao-corki.mp3" "server-received-lenna.png"
	
client-send-lenna:
	python3 dccnet-xfer.py -c ${HOST}:${PORT} "lenna.png" "client-received-corki.mp3"

server:
	python3 dccnet-xfer.py -s ${PORT} ${SERVER_INPUT} ${SERVER_OUTPUT}
	
client:
	python3 dccnet-xfer.py -c ${HOST}:${PORT} ${CLIENT_INPUT} ${CLIENT_OUTPUT}

md5:
	python3 dccnet-md5.py "rubick.snes.2advanced.dev:51565" "2021421869  :44:87407f792f59b7dde2bf51a0ae7216cf8c246a7169b52ac336bbf166938d91a1+2020054250  :44:50527ec32fc4c6fd5493533c67ce42f5fcad7bb59723976ff54acc6ae84385b8+2021421940  :44:a70a80b0528f580bb6c0a94ae37e3d8efdfb7adb9f939f3af675e9ea69694db4+f16d50fda86436470ba832a3f63525650dbd1fe021e867069f35ef4073d1b637"

debug:
	python3 debug.py
