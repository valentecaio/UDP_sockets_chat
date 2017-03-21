import socket
from sys import argv
from time import sleep
import messages

def listen_and_connect(socket):
    print('Waiting for connection...')
    socket.listen(1)
    conn, addr = socket.accept()
    print('Connected by', addr)
    return conn

def send_msg(msg, client, name):
    msg = msg.encode('utf-8')
    client.sendall(msg)
    print("Sent msg '" + msg.decode() + "' to client " + name)

def start_server(ip = 'localhost'):
    # instantiate socket and bind it to localhost
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    address = (ip, 1212)
    s.bind(address)

    # wait for client to connect
    sender = listen_and_connect(s)
    receiver = listen_and_connect(s)

    send_msg("I'm waiting your message", sender, 'sender')
    send_msg("I'm waiting the message", receiver, 'receiver')

    while 1:
        received_data = sender.recv(1024).decode()
        if not received_data: break
        print('Received:', received_data)
        send_msg(received_data, receiver, 'receiver')

if __name__ == '__main__':
    try:
        ip = argv[1]
        start_server(ip)
    except:
        start_server()
