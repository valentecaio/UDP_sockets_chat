# Echo client program
import socket
from time import sleep
import threading
import struct
import messages


address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)


''' thread functions '''


# used by user interface thread
def send_data():
	print("Type messages to send: \t")
	while 1:
		msg = input("")

		# This is a test function. To start the test you have to type "test".
		# A connection request will be packed and send.
		# TODO: check merge (this if)
		if msg == 'test':
			msg = messages.createConnectionRequest(0, 'asdfghjk')
		else: # to normal strings
			msg = msg.encode('utf-8')

		UDPsocket.sendto(msg, address_server)


# used by server listener thread
def receive_data():
	print('listening server')
	while 1:
		try:
			received_data, addr = UDPsocket.recvfrom(1024)
			print('Server:', received_data.decode())
			print('Unpacking message:')
			unpack_message(receive_data())
		except:
			continue


# This is a test to unpack a recieved packet and show it.
# TODO: check merge of this function
def unpack_message(msg):
	msg = struct.unpack('>BBBH8s', msg)
	print(msg[0])
	print(msg[1])
	print(msg[2])
	print(msg[3])
	print(msg[4].decode('UTF-8'))


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

