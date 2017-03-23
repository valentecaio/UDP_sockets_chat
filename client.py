# Echo client program
import socket
from time import sleep
import threading
import struct
import messages as m


address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
client_id = int()

''' thread functions '''


# used by user interface thread
def send_data():
	print("Type messages to send: \t")
	while 1:
		msg = input("")

		if 'CONNECT' in msg:
			username = msg[8:].strip()
			msg = m.createConnectionRequest(0, username)
		else: 	# to normal strings
			msg = msg.encode('utf-8')

		UDPsocket.sendto(msg, address_server)


# used by server listener thread
def receive_data():
	print('listening server')
	while 1:
		try:
			data, addr = UDPsocket.recvfrom(1024)

			# unpack header
			unpacked_data = m.unpack_protocol_header(data)
			msg_type = unpacked_data['type']

			# treat acknowledgement messages according to types
			if unpacked_data['A']:
				if msg_type == m.TYPE_USER_LIST_RESPONSE:
					# code enter here when receiving a userListResponse acknowledgement
					pass
				# elif ...

			# treat non-acknowledgement messages
			else:
				if msg_type == m.TYPE_CONNECTION_ACCEPT:
					# TODO: get user id from message content
					# I tried this way but it doesn't work
					# client_id = int( unpacked_data['content'].decode().strip() )

					# send Acknowledgment as response
					response = m.acknowledgement(m.TYPE_CONNECTION_ACCEPT, 0, client_id)
					UDPsocket.sendto(response, address_server)

				# default case, it's here only to help tests
				else:
					print('Received "' + data.decode() + '" from', addr)
					# send answer
					UDPsocket.sendto(response, address_server)

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

