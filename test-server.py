import socket
import time
import random

# Configurações do servidor
HOST = '127.0.0.1'
PORT = 65432

# Padrão de sincronização
SYNC_PATTERN = b'\xDC\xC0\x23\xC2'
SYNC_FRAME = SYNC_PATTERN + SYNC_PATTERN

# Função para criar um frame de dados
def create_frame(data, include_error=False):
    length = len(data).to_bytes(2, byteorder='big')
    frame_id = (random.randint(0, 65535)).to_bytes(2, byteorder='big')
    frame = SYNC_FRAME + length + frame_id + data
    if include_error:
        # Introduzindo um erro no campo de sincronização
        frame = b'\x00' + frame[1:]
    return frame

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f'Servidor escutando em {HOST}:{PORT}')
        
        conn, addr = server.accept()
        with conn:
            print('Conectado por', addr)
            while True:
                # Envia um frame correto
                data = b'Hello, this is a test frame!'
                frame = create_frame(data)
                conn.sendall(frame)
                time.sleep(1)  # Espera um pouco antes de enviar o próximo frame

                # Envia um frame com erro de sincronização
                frame_with_error = create_frame(data, include_error=True)
                conn.sendall(frame_with_error)
                time.sleep(1)  # Espera um pouco antes de enviar o próximo frame

if __name__ == "__main__":
    run_server()
