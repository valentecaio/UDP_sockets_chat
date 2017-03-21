# Echo client program
import socket
from time import sleep
from sys import argv
import threading

address_server = ('localhost', 1212)

''' thread functions '''

# used by user interface thread
def main_loop():
	while 1:
		msg = input("Type message to send\n")
		msg = msg.encode('utf-8')
		s.send(msg)


# used by server listener thread
def listen_server():
	print('listening server')
	while 1:
		received_msg = s.recv(1024)
		print('Received:', received_msg.decode())


def run(s):
	thread_listen = threading.Thread(target=listen_server)
	thread_listen.daemon = True
	thread_listen.start()

	thread_user = threading.Thread(target=main_loop)
	thread_user.daemon = True
	thread_user.start()

	# hang program execution
	while 1:
		sleep(10)


''' internal functions '''


# create client socket
def start_client(address_client):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(address_client)
	return s


# connect client to server
def connect(s, address_server):
	print('Trying to connect...')
	s.connect(address_server)
	print('Connected to server:', address_server)


''' main interface '''
if __name__ == '__main__':
	try:
		address_client = (argv[1], int(argv[2]) )
	except:
		address_server = ('localhost', 1212)
		address_client = ('localhost', 1414)
	s = start_client(address_client)
	connect(s, address_server)
	run(s)



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