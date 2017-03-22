import socket
from sys import argv
from time import sleep
import threading
import messages

clients = []
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_dress = ('localhost', 1212)


# add client to clients list
def add_client(addr):
	# avoid adding clients already added
	for client in clients:
		if client['addr'] == addr: 	# can't compair using 'is'
			return

	client = {'id': len(clients), 'addr': addr}
	clients.append(client)
	print('Connected to a new client: \t', client['id'], client['addr'])


# receive a normal string, code it and send to receivers list
def send_msg(msg, receivers):
	msg = msg.encode('utf-8')
	for client in receivers:
		UDPSock.sendto(msg, client['addr'])
		print("Sent msg '" + msg.decode() + "' to client " + str(client['id']))


def start_server():
	UDPSock.bind(server_dress)
	print("Server started at address", server_dress)


''' thread functions '''


def receive_data():
	while 1:
		# receive message
		received_data, addr = UDPSock.recvfrom(1024)
		if not received_data: break

		# add client to clients list
		add_client(addr)

		# generate answer and encode it
		reponse = 'Received "' + received_data.decode() + '"'
		print(reponse, 'from', addr)

		# send answer
		send_msg(reponse, clients)


def send_data():
	pass
	'''
		while 1:
		for client in clients:
			received_data = client['socket'].recvfrom(1024).decode()
			if not received_data: break
			print('Received:', received_data)
			send_msg(received_data, clients)
	'''

def run_threads():
	# start a thread to receive data
	sender_thread = threading.Thread(target=receive_data)
	sender_thread.daemon = True
	sender_thread.start()

	# start a thread to hang sending messages
	sender_thread = threading.Thread(target=send_data)
	sender_thread.daemon = True
	sender_thread.start()

	# hang program execution
	while 1:
		sleep(10)


if __name__ == '__main__':
	start_server()
	run_threads()
