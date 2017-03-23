import socket
from time import sleep
import threading
import messages
import struct
import queue

clients = []
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_dress = ('localhost', 1212)
messages_queue = queue.Queue()


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
def send_string(msg, receivers):
	msg = msg.encode('utf-8')
	for client in receivers:
		UDPSock.sendto(msg, client['addr'])
		print("Sent msg '" + msg.decode() + "' to client " + str(client['id']))


# This is a test to unpack and read the contant.
# After that another packet is packed (the same one in this case) and send again to all clients.
# TODO: check the merge of this function
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
		UDPSock.sendto(msg, client['addr'])
		print("Sent msg '" + msg.decode() + "' to client " + str(client['id']))


def start_server():
	UDPSock.bind(server_dress)
	print("Server started at address", server_dress)


''' thread functions '''


def receive_data():
	while 1:
		# receive message
		data, addr = UDPSock.recvfrom(1024)
		if not data: break

		messages_queue.put_nowait({'data': data, 'addr': addr})


def send_data():
	while 1:
		try:
			msg = messages_queue.get(block=False)
		except:
			continue

		data, addr = msg['data'], msg['addr']

		# add client to clients list
		add_client(addr)

		# this try tests the unpack function
		try:
			print(messages.unpack_protocol_header(data))
		except:
			pass

		# generate answer and encode it
		response = 'Received "' + data.decode() + '"'
		print(response, 'from', addr)

		# send answer
		send_string(response, clients)

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
