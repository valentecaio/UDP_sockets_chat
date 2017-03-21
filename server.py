import socket
from sys import argv
from time import sleep
import messages

clients = []


def listen_and_connect(s):
    print('Waiting for connection...')
    s.listen(1)
    conn, addr = s.accept()
    client = {'name': 'valente', 'socket': conn, 'addr': addr}
    print('Connected to a new client:\n\t', client['name'], client['addr'])
    clients.append(client)


def send_msg(msg, receivers):
    msg = msg.encode('utf-8')
    for client in receivers:
        client['socket'].sendall(msg)
        print("Sent msg '" + msg.decode() + "' to client " + client['name'])


def start_server(ip = 'localhost'):
    # instantiate socket and bind it to localhost
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    address = (ip, 1212)
    s.bind(address)
    print("Server started at address", address)
    return s


def run_server(s):
    # wait for client to connect
    listen_and_connect(s)
    listen_and_connect(s)

    while 1:
        received_data = clients[0]['socket'].recv(1024).decode()
        if not received_data: break
        print('Received:', received_data)

        send_msg(received_data, clients)

if __name__ == '__main__':
    try:
        ip = argv[1]
        s = start_server(ip)
    except:
        s = start_server()
    run_server(s)