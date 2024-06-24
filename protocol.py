import hashlib
import socket
import struct
import sys
import threading
from typing import Union #--> Garante que a variável seja de algum dos tipos indicados (evita confusões)



class DCCNET:
    def __init__(self, type, host, port, inputFile, outputFile) -> None:
        ''' 
        Cria um objeto DCCNET a partir de um frame recebido pelo servidor ou cliente.
        Para facilitar, os dados são trabalhados em bytes, não em bits.
        '''

        ############################################################################################################
        #    FORMATO DO FRAME em bits
        #    0        32       64        80        96       112   120
        #    +---/----+---/----+---------+---------+---------+-----+------ ... ---+
        #    |  SYNC  |  SYNC  | chksum  | length  | ID      |flags| DATA         |
        #    +---/----+---/----+---------+---------+---------+-----+------ ... ---+
        #
        #
        #    FORMATO DO FRAME em bytes
        #    0        4        8        10        12         14    15
        #    +---/----+---/----+---------+---------+---------+-----+------ ... ---+
        #    |  SYNC  |  SYNC  | chksum  | length  | ID      |flags| DATA         |
        #    +---/----+---/----+---------+---------+---------+-----+------ ... ---+
        #############################################################################################################

        # PARAMETROS DO FRAME
        self.sync_1: bytes = b''    # 4 bytes: 0-3
        self.sync_2: bytes = b''    # 4 bytes: 4-7
        self.chksum: bytes = b''    # 2 bytes: 8-9
        self.length: bytes = b''    # 2 bytes: 10-11 
        self.ID: bytes = b''        # 2 bytes: 12-13
        self.flag: bytes = b''      # 1 byte: 14
        self.data: bytes = b''      # X bytes: 15-...

        # PARAMETROS DO PROGRAMA
        self.type = type # tipos: -c = Cliente , -s = Servidor
        self.host = host
        self.port = port
        self.sock = None
        try:
            self.input = open(inputFile, "rb") # Entrada de dados
            self.output = open(outputFile, "wb") # Saída de dados
        except:
            print("Verifique se o nome dos arquivos de entrada e saída estão corretos!")
            sys.exit(0)
        
        # FLAGS DE CONTROLE
        self.control_flags = {
            'ACK': 0x80,        #Data reception acknowledgement
            'END': 0x40,        #End-of-transmission bit
            'RST': 0x20,        #Reset connection due to unrecoverable error.
            'reserved': 0x3f    #Reserved. Should be set to zero.
        }


        #SYNC - Padrão utilizado para detectar o inicio de cada frame
        self.sync = b'\xDC\xC0\x23\xC2' 
        self.last_id_sent: int = 1
        self.last_id_received: int = 0



    ############################################################################################################
    ######### GETTERS E SETTERS
    ############################################################################################################
    def get_current_frame(self)->bytes:
        '''
            Cria frame do DCCNET parte por parte.
        '''
        
        string_hex_frame = self.sync_1 + " " + self.sync_2 + " " + self.chksum + " " + self.length + " " + self.ID + " " + self.flag + " " + self.data
        
        hex_frame = string_hex_frame.replace(" ", "")
        hex_frame = bytes.fromhex(hex_frame)
        
        return  hex_frame
    

    ############################################################################################################
    ######### Métodos específicos do protocolo DCCNET
    ############################################################################################################

    def create_ack_frame(self, previous_ID):   
        '''
            Feame DCCNET sem dados, tamanho zero e flag ACK.
        '''

        # A construir!


        pass

    def create_data_frame(self, data:str, is_last_frame: bool=False):   
        '''
            Frame DCCNET padrão para transmissão de dados.
        '''
        length_of_data = len(data)

        self.sync_1 = self.sync.hex(" ")
        self.sync_2 = self.sync.hex(" ")
        self.chksum = b'\x00\x00'.hex(" ")
        self.length = length_of_data.to_bytes(2, byteorder='big').hex(" ")
        self.ID = (1-self.last_id_sent).to_bytes(2, byteorder='big').hex(" ")  # O id precisa variar enre 0 e 1 a cada pacote enviado
        self.flag = self.control_flags['reserved'].to_bytes(1, byteorder='big').hex(" ")
        self.data = data.encode('ascii').hex(" ")

        # Se for o último frame da mensagem, coloca a flag END
        if is_last_frame:
            self.set_flag = self.control_flags['END'].to_bytes(1, byteorder='big').hex(" ")

        self.print_frame()
        self.chksum = self.calc_checksum().hex(" ")
        
   
        
    def print_frame(self):
        '''
            Imprime os campos do frame atualmente preenchidos.
        '''
        print("\n-------------------FRAME----------------------")
        print(f"sync_1:   {self.sync_1}               # 4 bytes: 0-3")
        print(f"sync_2:   {self.sync_2}               # 4 bytes: 4-7")
        print(f"chksum:   {self.chksum}                     # 2 bytes: 8-9")
        print(f"length:   {self.length}                     # 2 bytes: 10-11")
        print(f"ID:   {self.ID}                         # 2 bytes: 12-13")
        print(f"flag:   {self.flag}                          # 1 byte: 14")
        print(f"data:   {self.data}  ")
        print(f"data in string format:   {bytes.fromhex(self.data).decode('ASCII')} ")
        print("---------------------------------------------\n")


    def calc_checksum(self) -> bytes:
        '''
            Calcula o internet checksum do frame passado como parâmetro.
        '''
        frame_input = self.get_current_frame()

        # Durante o cálculo do checksum, os bits do cabeçalho reservados para o checksum devem ser considerados como zero.
        self.chksum = b'\x00\x00'.hex(" ")
        
        if len(frame_input) % 2 != 0:
            frame_input += bytes([0])

        # Converte frame em palavras de 16 bits
        words = [frame_input[i] + (frame_input[i + 1] << 8) for i in range(0, len(frame_input), 2)]
        
        #  Calcula a soma em 32-bits e transforma em 16 bits
        checksum = sum(words)
        while checksum >> 16:
            checksum = (checksum & 0xFFFF) + (checksum >> 16)
        
        # Complemento de 1
        checksum = ~checksum & 0xFFFF
        
        return bytes(checksum)
    

    ############################################################################################################
    ######################################## Métodos de comunicação ############################################
    ############################################################################################################

    def establish_transmitter_socket(self) -> None:
        '''
            Cria socket UDP
        '''
        addr_info = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_DGRAM)

        for info in addr_info:
            addr_type, _, _, _, sockaddr = info
            try:
                # Create a UDP socket
                sock = socket.socket(addr_type, socket.SOCK_DGRAM)
                sock.settimeout(5)

                # Servidor é conectado ao cliente
                sock.bind(("", self.port)) 

                print(f"Server listening on {sockaddr}")

                # ========================================== #

                self.sock = sock
                self.sockaddr = sockaddr
                return
            
            except Exception as e:
                print("Failed to bind to", sockaddr, ":", e)
                continue
    
    
    # Close socket
    def stop(self):
        self.sock.close()


        print('Transmitter successfully shut down.')


    def send_frame_receive_ACK(self):
        '''
            Envia um frame e aguarda pelo ACK.
        '''
        waiting_ACK = False
        finished_sending = False

        while True:
            try:
                # --------------------------- Envio ------------------------------------
                if(not waiting_ACK and not finished_sending): # Se livre e não terminou de enviar, envie
                    self.send_frame()
                    waiting_ACK = True
                    finished_sending = True
                    break
                    #!!!!!!!!!!!!!!!!!!!!!!!!!!! implementar reenvio do pacote aqui !!!!!!!!!!!!!!!!!!!!!!!!!!!
                
                # --------------------------- Recebimento ------------------------------

                        # A frame can only be accepted if it is an acknowledgement frame for the last transmitted frame; 
                        # a data frame with an identifier (ID) different from that of the last received frame; 
                        # a retransmission of the last received frame; 
                        # or a reset frame.

                        # Recebe o pacote de resposta

                # --------------- Verifica checksum - se der erro: joga fora pacote, senão: continua recebendo ---------------------
                
                # Passa para a próxima execução (receber outro pacote), se este pacote vier com falha no checksum
                
                # Se for um ACK - pacote confirmado --> tudo ok
                # Se o ACK recebido for o do id esperado, confirme-o, senão (retransmissão de ack) , não faça nada

                # Se for um pacote de dados
                # Se o ID for o esperado, comece a receber o pacote


            except KeyboardInterrupt:
                self.imprimir("CTRL+C - Programa finalizado.")
                sys.exit(0)
            except socket.error as e:
                print("             -----------------------------------")
                print("             - Conexão fechada pelo outro lado -")
                print("             -----------------------------------")
                sys.exit(0)
            except Exception as e:
                print("Exceção desconhecida: " + str(e))
                sys.exit(0)




    def send_frame(self):
        data_count = 4096 #Tamanho máximo dos dados

        byte_read = self.input.read(1) # lê os 4096 bytes de um pacote
        is_last_frame = False
        message = ""

        # Enquanto tiver dados para serem lidos no arquivo txt, lê um byte a agrega à mensagem
        while (data_count > 0 and byte_read):
            if byte_read == b'\n':
                is_last_frame = True 
                message += ""
                data_count -= 1
            else:
                message += byte_read.decode('ascii')
                data_count -= 1 

            if data_count > 0:
                byte_read = self.input.read(1)

        if not byte_read: # Fim da leitura do arquivo de entrada (input)
            #self.input.close()
            self.terminouEnviar = True

        # Cria o frame de dados (o checksum é calculado internamente)
        self.create_data_frame(message, is_last_frame)

        # envia o pacote
        try:
            target_addr = (self.host, self.port)
            self.sock.sendto(self.get_current_frame(), target_addr)
            print(f"Sent data to {target_addr}")
        except Exception as e:
            print(f"Failed to send data to {target_addr}: {e}")

        # Vai alterando os bits da flag a cada envio de frame
        self.last_id_sent = ~self.last_id_sent

        print("Pacote transmitido!")


        
if __name__ == "__main__":
    tipo = "-s" 
    host = 'localhost'
    port = 12345
    input_file = "server-input.txt"
    output_file = "output.txt"
    
    ## Cria um servidor com o protocolo DCCNET
    servidor = DCCNET(tipo, host, port, input_file, output_file)# Instancia a classe
    servidor.establish_transmitter_socket() # Cria socket como servidor
    servidor.send_frame_receive_ACK() # Inicia o processo de transmitir seus pacotes e receber pacotes do outro

    #### Próximos passos
    # Terminar de implementar método de envio de pacotes (método send_frame_receive_ACK())
    # Manter o servidor sempre escutando uma conexão do cliente
    # Criar os outros tipos de frame (se basear em create_data_frame())
    # Criar cliente
