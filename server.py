import queue
import socket
import threading
from time import sleep

import messages as m

try:
	from pprint import pprint
except:
	pprint = print

clients = {}
next_id = 0
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', 1212)
messages_queue = queue.Queue()

# constants
ST_CONNECTING = 0
ST_CONNECTED = 1

PUBLIC_GROUP = 1

#checks if username is already in the list. returns True if username is ok and fals if there is already somebody using it
def check_username(username):
	for id, client in clients.items():
		if client['username'] == username:
			return False
	return True


# add client to clients list
def connect_client(addr, username):

	# add client to clients dict
	global next_id
	client_id = next_id
	next_id += 1

	client = {'id': client_id, 'addr': addr, 'username': username, 'state': ST_CONNECTING, 'group': PUBLIC_GROUP}
	clients[str(client_id)] = client

	print('Connected to a new client: \t', client)
	return client


# receive a coded message and send it to receivers list
def send_message(msg, receivers):
	for id, client in receivers.items():
		UDPSock.sendto(msg, client['addr'])
		print("Sent msg to client " + str(id))


# function to update the list of all users if somebody joined or changed status.
# Input is a dictionary of the users that changed
def update_user_list(updated_users):
	for id, client in clients.items():
		msg = m.createUpdateList(0, updated_users)
		UDPSock.sendto(msg, client['addr'])
	return


''' thread functions '''


def receive_data():
	while 1:
		# receive message
		data, addr = UDPSock.recvfrom(1024)
		if not data: break

		# put new message in the queue
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

		# treat acknowledgement messages according to types
		if unpacked_data['A']:
			if msg_type == m.TYPE_CONNECTION_ACCEPT:
				# code enter here when receiving a connectionAccept acknowledgement
				# change client state to connected
				client = clients[ str(unpacked_data['sourceID']) ]
				client['state'] = ST_CONNECTED
				# update list of other users
				updated_user = {str(unpacked_data['sourceID']): client}
				update_user_list(updated_user)
			elif msg_type == m.TYPE_USER_LIST_RESPONSE:
				# code enter here when receiving a userListResponse acknowledgement
				pass
			# elif ...

		# treat non-acknowledgement messages
		else:
			if msg_type == m.TYPE_CONNECTION_REQUEST:
				# get username from message content
				username = unpacked_data['content'].decode().strip()
				#checks username and responses according to that check (allows or denies connection)
				if check_username(username) == True:
					if len(clients) < 250:
						# add client to clients list
						client = connect_client(addr, username)
						# send ConnectionAccept as response
						response = m.createConnectionAccept(0, client['id'])
						UDPSock.sendto(response, client['addr'])
					else:
						#send error code 0 for maximum of members on the server
						response = m.createConnectionReject(0,0)
						UDPSock.sendto(response, addr)
				else:
					#send error code 1 for username already taken
					response = m.createConnectionReject(0,1)
					UDPSock.sendto(response, addr)

			elif msg_type == m.TYPE_DATA_MESSAGE:
				# get message text
				# should send ack
				content = unpacked_data['content']
				text = content[2:]
				print("%s >> %s" % (unpacked_data['sourceID'], text.decode()))
				groupID = unpacked_data['groupID']

				# resend it to users in same group
				receivers = {}

				for id,client in clients.items():
					if client['group'] == groupID:
						receivers[id] = clients[id]
				send_message(data, receivers)

			elif msg_type == m.TYPE_USER_LIST_REQUEST:
				# send user list
				client = clients[ str(unpacked_data['sourceID']) ]
				response = m.createUserListResponse(0, client['id'], clients)
				print('send user list')
				UDPSock.sendto(response, client['addr'])

			elif msg_type == m.TYPE_DISCONNECTION_REQUEST:
				client = clients[str(unpacked_data['sourceID'])]
				del clients[str(unpacked_data['sourceID'])]
				response = m.acknowledgement(msg_type, 0, client['id'])
				UDPSock.sendto(response, client['addr'])
				# tell other clients that user disconnected
				update_disconnection = m.updateDissconnction(0, unpacked_data['sourceID'])
				send_message(update_disconnection, clients)

			elif msg_type == m.TYPE_GROUP_CREATION_REQUEST:
				client_id = (unpacked_data['sourceID'])
				group_type, members = m.unpack_group_creation_request(data)
				print("User %s is inviting members %s to a group of type %s"
					  % (client_id, members, group_type))



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
