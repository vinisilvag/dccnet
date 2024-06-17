HOST=127.0.1.1
PORT=6542
SERVER_INPUT="server-input.txt"
SERVER_OUTPUT="server-output.txt"
CLIENT_INPUT="client-input.txt"
CLIENT_OUTPUT="client-output.txt"

server:
	python3 dccnet-xfer.py -s ${PORT} ${SERVER_INPUT} ${SERVER_OUTPUT}
	
client:
	python3 dccnet-xfer.py -c ${HOST}:${PORT} ${CLIENT_INPUT} ${CLIENT_OUTPUT}

md5:
	python3 dccnet-md5.py rubick.snes.2advanced.dev:51563

debug:
	python3 debug.py
