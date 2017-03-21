# Echo client program
import socket
from time import sleep
from sys import argv


def start_client(ip='localhost', server_port=1212):
	address_server = (ip, server_port)
	address_client = ('localhost', 1414)

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(address_client)

	print('Trying to connect...')
	s.connect(address_server)
	print('Connected to server:', address_server)

	while 1:
		received_msg = s.recv(1024)
		print('Received:', received_msg.decode())

if __name__ == '__main__':
	try:
		ip = argv[1]
		server_port = argv[2]
		start_client(ip, int(server_port))
	except:
		start_client()



''' sender

# Echo client program
import socket
from time import sleep
from sys import argv


def start_client(ip='localhost', server_port=1212):
	address_server = (ip, server_port)
	address_client = ('localhost', 1313)

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(address_client)

	print('Trying to connect...')
	s.connect(address_server)
	print('Connected to server:', address_server)

	received_msg = s.recv(1024)
	print('Received:', received_msg.decode())

	while 1:
		msg = input('type something to send it: ')
		msg = msg.encode('utf-8')
		s.send(msg)

if __name__ == '__main__':
	try:
		ip = argv[1]
		server_port = argv[2]
		start_client(ip, int(server_port))
	except:
		start_client()


'''