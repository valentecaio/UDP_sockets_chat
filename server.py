import queue
import socket
import threading
from time import sleep
import time

import messages as m

try:
	from pprint import pprint
except:
	pprint = print


# constants
ST_CONNECTING = 0
ST_CONNECTED = 1


clients = {}
groups = {m.PUBLIC_GROUP_ID: {'creator': m.NOBODY_ID, 'id': m.PUBLIC_GROUP_ID,
							  'type': m.GROUP_CENTRALIZED, 'members': []}}
group_invitations = {}
next_client_id = 1
next_group_id = 2
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', 1212)
messages_queue = queue.Queue()


'''waiting variables'''
#is set to 1 if we wait for an ack
waiting_flag = 0
#queue that is used if an ack should arrive
waiting_queue = queue.Queue()


'''Waiting and resend functions'''

#This function takes type and source_id of the ack that is expected aswell as the massege that may have to be resend and the adress to which it may have to be resend.
#We are waiting for 3s to get the correct ack an store all different messages that are arriving in that time. They will be put back on the queue to be treated later.																									---------------------------HHHIIIIEEEEEERRRRRRRRR-----------------------
def wait_for_acknowledgement(type, source_id, resend_data, addr):
	global waiting_flag
	waiting_flag = 1
	wrong_messages = []
	breaker = 0
	#we try 3 times before giving up
	for i in range(3):
		#call waiter function
		status, wrong_messages = waiter(type, source_id, wrong_messages)

		if status == 'received':
			return

		#resend the message (3 times)
		print('resend')
		UDPSock.sendto(resend_data, addr)
	print('could not send data')
	#if we did not receive the ack we also reset the queue and return
	waiting_flag = 0

	# empty the waiting queue if there are still elements in there
	while waiting_queue.empty() == False:
		input = waiting_queue.get(block=False)
		received_data, received_addr = input['data'], input['addr']
		wrong_message = {}
		wrong_message['addr'] = received_addr
		wrong_message['data'] = received_data
		wrong_messages.append(wrong_message)

	# put all the messages back
	for wrong_message in wrong_messages:
		messages_queue.put_nowait({'data': wrong_message['data'], 'addr': wrong_message['addr']})
	return


def waiter(type, source_id, wrong_messages):
	global waiting_flag
	# 3 seconds from now
	print('start looping')
	timeout = time.time() + 10
	# get messages from waiting queue
	while True:

		# if more than 3 seconds passed we break the while loop
		if time.time() > timeout:
			print('timeout for ack')
			status = 'resend'
			return (status, wrong_messages)
		try:
			input = waiting_queue.get(block=False)
			received_data, received_addr = input['data'], input['addr']

		except:
			continue

		header = m.unpack_header(received_data)
		receiver_type = header['type']
		receiver_source_id = header['sourceID']
		print(receiver_source_id)
		print(source_id)

		# if we received the correct ack, pack wrong messages back in the queue and return
		if receiver_type == type and receiver_source_id == source_id:
			# stop input in the waiting queue
			waiting_flag = 0
			# empty the waiting queue if there are still elemnts in there
			while waiting_queue.empty() == False:
				input = waiting_queue.get(block=False)
				received_data, received_addr = input['data'], input['addr']
				wrong_message = {}
				wrong_message['addr'] = received_addr
				wrong_message['data'] = received_data
				wrong_messages.append(wrong_message)

			# put all the messages back in the actual queue
			for wrong_message in wrong_messages:
				messages_queue.put_nowait({'data': wrong_message['data'], 'addr': wrong_message['addr']})

			status = 'received'
			return(status, wrong_messages)

		# pack wrong message in the wrong messages list
		else:
			print('pack wrong package in list')
			wrong_message = {}
			wrong_message['addr'] = received_addr
			wrong_message['data'] = received_data
			wrong_messages.append(wrong_message)



''' functions for list administration '''

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

	client = {'id': client_id, 'addr': addr, 'username': username, 'state': ST_CONNECTING, 'group': m.PUBLIC_GROUP_ID}
	clients[client_id] = client

	# add new client to public group
	groups[m.PUBLIC_GROUP_ID]['members'].append(client)

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
		wait_for_acknowledgement(m.TYPE_UPDATE_LIST, client['id'], msg, client['addr'])
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

	groups[old_group_id]['members'].remove(user)
	groups[new_group_id]['members'].append(user)

	new_group = groups[new_group_id]
	old_group = groups[old_group_id]


	user['group'] = new_group['id']

	#If only one user remains delete group and send a group dissolution, pack that guy in the public group an inform everybody about the changes.
	if len(old_group['members']) == 1 and old_group_id != m.PUBLIC_GROUP_ID:

		#only member in the old group
		user_left = old_group['members'][0]

		#send group dissolution
		msg = m.groupDissolution(0, old_group_id)
		UDPSock.sendto(msg, user_left['addr'])

		#delete old group in the group list
		del groups[old_group_id]

		#change group of old user to public group
		groups[m.PUBLIC_GROUP_ID]['members'].append(user_left)
		clients[user_left['id']]['group']=m.PUBLIC_GROUP_ID

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
		if waiting_flag == 0:
			messages_queue.put_nowait({'data': data, 'addr': addr})
		else:
			waiting_queue.put_nowait({'data': data, 'addr': addr})

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
				global group_invitations
				# if group doesn't exist, create it and add creator to it
				if group_id not in groups:

					# create new group
					new_group = {}
					new_group['creator']= source_id
					new_group['id'] = group_id
					new_group['type'] = group_type
					new_group['members'] = []
					groups[group_id] = new_group

					# remove user from invitation list
					accept_member = clients[member_id]
					group_invitations[group_id]['members'].remove(accept_member['id'])

					# change creator to new group
					creator_id = groups[group_id]['creator']
					change_group(creator_id, group_id)


				else:
					# remove user from invitation list
					accept_member = clients[member_id]
					group_invitations[group_id]['members'].remove(accept_member['id'])

					#delete invitation if everybody responded
				if len(group_invitations[group_id]['members']) == 0:
					del group_invitations[group_id]
					print('invitation has been deleted')

				# send an creation accept to creator
				msg = m.groupCreationAccept(0, creator_id,
												groups[group_id]['type'],
												group_id)
				UDPSock.sendto(msg, clients[creator_id]['addr'])
				#change group of member
				change_group(member_id, group_id)


				# will change user to public group to use the functionalities of the cahnge_group function and delete him after that.
			elif msg_type == m.TYPE_DISCONNECTION_REQUEST:
				print(str(source_id) + ': DISCONNECTION_REQUEST')

				#changeS group to public group. Necessary because the function change_group takes care that there is more than one user in a group.
				client = clients[source_id]
				change_group(source_id, m.PUBLIC_GROUP_ID)

				# send acknowledgement
				response = m.acknowledgement(msg_type, 0, source_id)
				UDPSock.sendto(response, addr)

				# tell other clients that user disconnected (all clients, not only in a group)
				update_disconnection = m.updateDisconnection(0, source_id)
				for id, client in clients.items():
					UDPSock.sendto(update_disconnection, client['addr'])
					print('Sent UPDATE_DISCONNECTION to user ' + str(id))

				# remove client from group and client lists (the del function works well for me, maybe there was a different problem)
				groups[m.PUBLIC_GROUP_ID]['members'].remove(client)
				del clients[source_id]

			elif msg_type == m.TYPE_GROUP_CREATION_REQUEST:
				print(str(source_id) + ': GROUP_CREATION_REQUEST')
				group_type, members = m.unpack_group_creation_request(data)
				print("User %s is inviting members %s to a group of type %s"
					  % (source_id, members, group_type))

				ack = m.acknowledgement(m.TYPE_GROUP_CREATION_REQUEST, 0, 0x00)  #TODO: server acks always have the source id 0. That has to be changed for other acks. Id can be changed to test functionality of the resend function
				UDPSock.sendto(ack,clients[source_id]['addr'])

				# get an ID to new group
				group_id = next_group_id
				next_group_id += 1

				# add group to stand-by invitations dict
				group_invitations[group_id] = {'creator': source_id,
											   'id': group_id,
											   'type': group_type,
											   'members': members}

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
				reject_member = clients[member_id]
				group_invitations[group_id]['members'].remove(reject_member['id'])

				# delete from group_invitation dict if nobody accepted
				if len(group_invitations[group_id]['members']) == 0 and group_id not in groups:
					msg = m.groupInvitationReject(0, group_invitations[group_id]['creator'],                            # put flag if last user rejected
											  group_invitations[group_id]['type'],
										  group_id, member_id, 1)
					del group_invitations[group_id]
					print('invitation has been deleted')
				else:
					msg = m.groupInvitationReject(0, group_invitations[group_id]['creator'],
												  group_invitations[group_id]['type'],
												  group_id, member_id)

				UDPSock.sendto(msg, clients[source_id]['addr'])



			elif msg_type == m.TYPE_GROUP_DISJOINT_REQUEST:
				change_group(source_id, m.PUBLIC_GROUP_ID)
				print(str(source_id) + ': DISJOINT GROUP')


				# send acknowledgement
				response = m.acknowledgement(msg_type, 0, source_id)
				UDPSock.sendto(response, addr)





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
