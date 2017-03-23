# Echo client program
import socket
from time import sleep
import threading
import struct
import messages as m


address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
client_id = 0
client_group = 0

''' thread functions '''


# used by user interface thread
def read_keyboard():
	print("Type messages to send: \t")
	while 1:
		user_input = input("")

		if 'CONNECT' in user_input:
			username = user_input[8:].strip()
			msg = m.createConnectionRequest(0, username)

		elif 'SEND' in user_input:
			text = user_input[5:].encode('utf-8')
			msg = m.createDataMessage(0, client_id, client_group, text)


		else:
			print("This is not a valid command. Type HELP to get some help.")
			continue

		UDPsocket.sendto(msg, address_server)


# used by server listener thread
def main_loop():
	print('listening server')
	while 1:
		try:
			data, addr = UDPsocket.recvfrom(1024)

			# unpack header
			unpacked_data = m.unpack_protocol_header(data)									#that has to be different for each message
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

					global client_id 													#needed to modify a global variable
					unpacked_data = m.unpack_connection_accept(data)					#a new unpack function was needed, because the ID was unpacked as a string. I think that is the reason it didn't work.
					client_id = int(unpacked_data['clientID'])

					# send Acknowledgment as response
					response = m.acknowledgement(m.TYPE_CONNECTION_ACCEPT, 0, client_id)
					UDPsocket.sendto(response, address_server)

				if msg_type == m.TYPE_DATA_MESSAGE:
					content = unpacked_data['content']
					text = content[2:]
					print("%s: %s" % (unpacked_data['sourceID'], text.decode()))
				# default case, it's here only to help tests
				else:
					print('Received "' + data.decode() + '" from', addr)
					# send answer
					UDPsocket.sendto(response, address_server)

		except:
			continue


def run_threads():
	thread_user = threading.Thread(target=read_keyboard)
	thread_user.daemon = True
	thread_user.start()

	thread_listen = threading.Thread(target=main_loop)
	thread_listen.daemon = True
	thread_listen.start()

	# hang program execution
	while 1:
		sleep(10)


''' main interface '''
if __name__ == '__main__':
	run_threads()

