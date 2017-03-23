import socket
from time import sleep
import threading
import messages as m
import struct
import queue

clients = []
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', 1212)
messages_queue = queue.Queue()

# clients state constants
ST_CONNECTING = 0
ST_CONNECTED = 1

PUBLIC_GROUP = 1


# add client to clients list
# TODO: usernameAlreadyExists and invalidUsername
def add_client(addr, username):
	# avoid adding clients already added
	for client in clients:
		if client['addr'] == addr: 	# can't compair using 'is'
			return

	client = {'id': len(clients), 'addr': addr, 'username': username, 'state': ST_CONNECTING, 'group': PUBLIC_GROUP}
	clients.append(client)
	print('Connected to a new client: \t', client)
	return client


# receive a coded message and send it to receivers list
def send_message(msg, receivers):
	for client in receivers:
		UDPSock.sendto(msg, client['addr'])
		print("Sent msg to client " + str(client['id']))


''' thread functions '''


def receive_data():
	while 1:
		# receive message
		data, addr = UDPSock.recvfrom(1024)
		if not data: break

		messages_queue.put_nowait({'data': data, 'addr': addr})


def send_data():
	while 1:
		# try to get a message from the queue
		# if there's no message, try again without blocking
		try:
			input = messages_queue.get(block=False)
			data, addr = input['data'], input['addr']
		except:
			continue

		# unpack header
		unpacked_data = m.unpack_protocol_header(data)
		msg_type = unpacked_data['type']

		# treat message according to type
		if msg_type == m.TYPE_CONNECTION_REQUEST:
			username = unpacked_data['content'].decode()

			# add client to clients list
			client = add_client(addr, username)

			# send ConnectionAccept as response
			response = m.createConnectionAccept(0, client['id'])
			send_message(response, [client])

		elif msg_type == m.TYPE_ACKNOWLEGEMENT:
			pass
		else: # default case, it's here only to help tests
			print('Received "' + data.decode() + '" from', addr)

			# send answer
			send_message(data, clients)

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
	UDPSock.bind(server_address)
	print("Server started at address", server_address)
	run_threads()
