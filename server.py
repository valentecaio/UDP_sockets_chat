import socket
from sys import argv
from time import sleep
import threading
import messages
import ctypes
import struct

clients = []
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# add client to clients list
def add_client(sock, addr):
	client = {'id': len(clients), 'socket': sock, 'addr': addr}
	clients.append(client)
	print('Connected to a new client: \t', client['id'], client['addr'])


#This is a test to unpack and read the contant. After that another packet is packed (the same one in this case) and send again to all clients.
def send_msg(msg, receivers):
	#msg = msg.encode('utf-8')
	msg = struct.unpack('>BBBH8s', msg)
	print(msg[0])
	print(msg[1])
	print(msg[2])
	print(msg[3])
	print(msg[4].decode('UTF-8'))
	msg = messages.createConnectionRequest(0, 'asdfghjk')



	for client in receivers:
		client['socket'].sendall(msg)
		#print("Sent msg '" + msg.decode() + "' to client " + str(client['id']))


def start_server():
	# instantiate socket and bind it to localhost
	address = ('localhost', 1212)
	server_socket.bind(address)
	print("Server started at address", address)
	return server_socket


''' thread functions '''

# used by connection listener thread
# listen to connection requests and accept them
def listen_connection_requests():
	while 1:
		# listen to connection requests and accept them
		server_socket.listen(1)
		conn, addr = server_socket.accept()
		add_client(conn, addr)


def main_loop():
	while 1:
		for client in clients:
			received_data = client['socket'].recv(1024)
			if not received_data: break
			print('Received:', received_data)
			send_msg(received_data, clients)


def run(s):
	# start a thread to hang connection requests
	thread_connection = threading.Thread(target=listen_connection_requests)
	thread_connection.daemon = True
	thread_connection.start()

	# start a thread to hang connected users demands
	thread_main = threading.Thread(target=main_loop)
	thread_main.daemon = True
	thread_main.start()

	# hang program execution
	while 1:
		sleep(10)


if __name__ == '__main__':
	server_socket = start_server()
	run(server_socket)
