# Echo client program
import socket
from time import sleep
import threading
import struct
import messages as m


address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)


''' thread functions '''


# used by user interface thread
def send_data():
	print("Type messages to send: \t")
	while 1:
		msg = input("")

		if 'CONNECT' in msg:
			username = msg[8:].strip()
			msg = m.createConnectionRequest(0, username)
		else: # to normal strings
			msg = msg.encode('utf-8')

		UDPsocket.sendto(msg, address_server)


# used by server listener thread
def receive_data():
	print('listening server')
	while 1:
		try:
			data, addr = UDPsocket.recvfrom(1024)
			print('Server:', data.decode())
			print('Unpacking message:')
			m.unpack_protocol_header(data)
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

