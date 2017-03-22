# Echo client program
import socket
from time import sleep
from sys import argv
import threading

address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)


''' thread functions '''


# used by user interface thread
def send_data():
	print("Type messages to send: \t")
	while 1:
		msg = input("")
		msg = msg.encode('utf-8')
		UDPsocket.sendto(msg, address_server)


# used by server listener thread
def receive_data():
	print('listening server')
	while 1:
		try:
			received_data, addr = UDPsocket.recvfrom(1024)
			print('Server:', received_data.decode())
		except:
			continue


def run_threads():
	thread_user = threading.Thread(target=send_data)
	thread_user.daemon = True
	thread_user.start()

	thread_listen = threading.Thread(target=receive_data)
	thread_listen.daemon = True
	thread_listen.start()

	# hang program execution
	while 1:
		sleep(10)


''' main interface '''
if __name__ == '__main__':
	run_threads()
