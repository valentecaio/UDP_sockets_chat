import queue
import socket
import threading
from time import sleep

import messages as m

try:
	from pprint import pprint
except:
	pprint = print


# constants
ST_CONNECTING = 0
ST_CONNECTED = 1
PUBLIC_GROUP_ID = 1
NOBODY_ID = -1
TYPE_PUBLIC = 0
TYPE_PRIVATE = 1


clients = {}
groups = {PUBLIC_GROUP_ID: {'creator': NOBODY_ID, 'id': PUBLIC_GROUP_ID, 'type': TYPE_PUBLIC, 'members': []}}
group_invitations = {}
next_client_id = 1
next_group_id = 2
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', 1212)
messages_queue = queue.Queue()





#checks if username is already in the list. returns True if username is ok and false if there is already somebody using it
def check_username(username):
	for id, client in clients.items():
		if client['username'] == username:
			return False
	return True


# add client to clients list
def connect_client(addr, username):
	# add client to clients dict
	global next_client_id
	client_id = next_client_id
	next_client_id += 1

	client = {'id': client_id, 'addr': addr, 'username': username, 'state': ST_CONNECTING, 'group': PUBLIC_GROUP_ID}
	clients[client_id] = client

	# add new client to public group
	groups[PUBLIC_GROUP_ID]['members'].append(client)

	print('Connected to a new client: \t', client)
	return client


# receive a coded message and send it to receivers list
def send_message(msg, group_id):
	global groups
	receivers = groups[group_id]['members']
	for client in receivers:
		UDPSock.sendto(msg, client['addr'])
		print("Sent msg to client " + str(client['id']))


# function to update the list of all users if somebody joined or changed status.
# Input is a dictionary of the users that changed
def update_user_list(updated_users):
	for id, client in clients.items():
		msg = m.createUpdateList(0, updated_users)
		UDPSock.sendto(msg, client['addr'])
		print('Sent UPDATE_LIST to user ' + str(id))
	return

#This function changes the group of a user.
#It takes care that a group dissolution will be initiated if only one user is left (except of course for the public group)
def change_group(user_id, new_group_id):

	#change groups on the server
	global clients
	global groups
	user = clients[user_id]
	old_group_id = user['group']
	changed_users = {}

	new_group = groups[new_group_id]
	old_group = groups[old_group_id]

	old_group['members'].remove(user)
	new_group['members'].append(user)

	user['group'] = new_group['id']

	#If only one user remains delete group and send a group dissolution, pack that guy in the public group an inform everybody about the changes.
	if len(old_group['members']) == 1 and old_group_id != PUBLIC_GROUP_ID:

		#only member in the old group
		user_left = old_group['members'][0]

		#send group dissolution
		msg = m.groupDissolution(0, old_group_id)
		UDPSock.sendto(msg, user_left['addr'])

		#delete old group in the group list
		del groups[old_group_id]

		#change group of old user to public group
		groups[PUBLIC_GROUP_ID]['members'].append(user_left)
		clients[user_left['id']]['group']=PUBLIC_GROUP_ID

		#update changes for everyone
		changed_users[str(user['id'])] = user
		changed_users[str(user_left['id'])] = user_left
		update_user_list(changed_users)

	else:
		changed_users[str(user['id'])] = user
		update_user_list(changed_users)


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
		header = m.unpack_header(data)
		msg_type = header['type']
		source_id = header['sourceID']
		group_id = header['groupID']

		global next_group_id
		global groups
		global clients

		# treat acknowledgement messages according to types
		if header['A']:
			print(str(source_id) + ': ACKNOWLEDGEMENT of type ' + str(msg_type))
			if msg_type == m.TYPE_CONNECTION_ACCEPT:
				# code enter here when receiving a connectionAccept acknowledgement
				# change client state to connected
				client = clients[source_id]
				client['state'] = ST_CONNECTED
				# update list of other users
				updated_user = {source_id: client}
				update_user_list(updated_user)
			elif msg_type == m.TYPE_USER_LIST_RESPONSE:
				pass
		# treat non-acknowledgement messages
		else:
			if msg_type == m.TYPE_CONNECTION_REQUEST:
				print(str(source_id) + ': CONNECTION_REQUEST')
				# get username from message content
				username = header['content'].decode().strip()
				#checks username and responses according to that check (allows or denies connection)
				if check_username(username) == True:
					if len(clients) < 250:
						# add client to clients list
						client = connect_client(addr, username)
						# send ConnectionAccept as response
						response = m.createConnectionAccept(0, client['id'])
						UDPSock.sendto(response, client['addr'])
						print('sent CONNECTION_ACCEPT to client')
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
				content = header['content']
				text = content[2:].decode()
				username = clients[source_id]['username']
				print("%s [%s]: %s" % (username, str(source_id), text))

				# resend it to users in same group
				send_message(data, group_id)

			elif msg_type == m.TYPE_USER_LIST_REQUEST:
				print(str(source_id) + ': USER_LIST_REQUEST')
				# send user list
				group_id = clients[source_id]['group']
				# TODO: it's always sending clients list --> don't see the problem. This message is only sended once, when somebody connects, so he needs the list.
				response = m.createUserListResponse(0, source_id, clients)
				print('send USER_LIST_REQUEST to client ' + str(source_id))
				UDPSock.sendto(response, clients[source_id]['addr'])

			elif msg_type == m.TYPE_GROUP_INVITATION_ACCEPT:
				print(str(source_id) + ': GROUP_INVITATION_ACCEPT')
				group_type, group_id, member_id = \
					m.unpack_group_invitation_accept(data)
				updated_users = {}

				# if group doesn't exist, create it and add creator to it
				if group_id not in groups:
					# remove group from standby dict and put it on active groups dict
					groups[group_id] = group_invitations.pop(group_id)

					# change creator to new group
					creator_id = groups[group_id]['creator']
					change_group(creator_id, group_id)
					updated_users[creator_id] = clients[creator_id]

					# send an creation accept to creator
					msg = m.groupCreationAccept(0, creator_id,
												groups[group_id]['type'],
												group_id)
					UDPSock.sendto(msg, clients[creator_id]['addr'])
				change_group(member_id, group_id)


				# TODO: this only works to groups with 2 persons --> don't understand the problem :/

				# add source client to group
				#change_group(source_id, group_id)
				#updated_users[source_id] = clients[source_id]

				# update all users in group --> changed that. I think he has to update all of the users.
				#update_user_list(updated_users) --> should be now included in the change_group function

				#msg = m.createUpdateList(0, updated_users)
				#send_message(msg, group_id)

				# TODO: warn users from old groups that both users left

				# will change user to public group to use the functionalities of the cahnge_group function and delete him after that.
			elif msg_type == m.TYPE_DISCONNECTION_REQUEST:
				print(str(source_id) + ': DISCONNECTION_REQUEST')

				#changeS group to public group. Necessary because the function change_group takes care that there is more than one user in a group.
				client = clients[source_id]
				change_group(source_id, PUBLIC_GROUP_ID)

				# send acknowledgement
				response = m.acknowledgement(msg_type, 0, source_id)
				UDPSock.sendto(response, addr)

				# tell other clients that user disconnected (all clients, not only in a group)
				update_disconnection = m.updateDisconnection(0, source_id)
				for id, client in clients.items():
					UDPSock.sendto(update_disconnection, client['addr'])
					print('Sent UPDATE_DISCONNECTION to user ' + str(id))

				# remove client from group and client lists (the del function works well for me, maybe there was a different problem)
				groups[PUBLIC_GROUP_ID]['members'].remove(client)
				del clients[source_id]

			elif msg_type == m.TYPE_GROUP_CREATION_REQUEST:
				print(str(source_id) + ': GROUP_CREATION_REQUEST')
				group_type, members = m.unpack_group_creation_request(data)
				print("User %s is inviting members %s to a group of type %s"
					  % (source_id, members, group_type))

				ack = m.acknowledgement(m.TYPE_GROUP_CREATION_REQUEST, 0, source_id)
				UDPSock.sendto(ack,clients[source_id]['addr'])

				# get an ID to new group
				group_id = next_group_id
				next_group_id += 1

				# add group to stand-by invitations dict
				group_invitations[group_id] = {'creator': source_id,
											   'id': group_id,
											   'type': group_type,
											   'members': []}

				# invite members to group
				for id in members:
					invitation = m.groupInvitationRequest(0, source_id,
														  group_type, group_id,
														  id)
					UDPSock.sendto(invitation, clients[id]['addr'])
					print('Sent GROUP_INVITATION_REQUEST to client ' + str(id))

			elif msg_type == m.TYPE_GROUP_INVITATION_REJECT:
				print(str(source_id) + ': GROUP_INVITATION_REJECT')
				group_type, group_id, member_id = \
					m.unpack_group_invitation_accept(data)

				#delete this member in the group_invitation dict
				#reject_member = clients[source_id]															gives error that not in list
				#group_invitations[group_id]['members'].remove(reject_member)

				#send rejection to user that asked
				msg = m.groupInvitationReject(0, group_invitations[group_id]['creator'],
											group_invitations[group_id]['type'],
											group_id, member_id)
				UDPSock.sendto(msg, clients[source_id]['addr'])
				# delete from group_invitation dict if only one member left
				if len(group_invitations[group_id]['members']) == 1:
					del group_invitations[group_id]





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
