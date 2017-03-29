import queue
import socket
import threading
import time
from time import sleep

import constants as c
import messages as m
from core import *
from socerr import socerr

try:
	from pprint import pprint
except:
	pprint = print

# this value can be changed to increase the failure rate
SOCKET_ERROR_RATE = 0

clients = {}
groups = {c.PUBLIC_GROUP_ID: Group(id=c.PUBLIC_GROUP_ID, creator_id=c.NOBODY_ID,
								   type=c.GROUP_CENTRALIZED, members=[])}
group_invitations = {}
next_client_id = 1
next_group_id = 2
UDPSock = socerr(socket.AF_INET, socket.SOCK_DGRAM, SOCKET_ERROR_RATE) #TODO: the value which is zero can be changed to increase the failure rate (just a info)
server_address = ('localhost', 1212)
messages_queue = queue.Queue()


'''waiting variables'''
#is set to True if we wait for an ack
waiting_flag = False
#queue that is used if an ack should arrive
waiting_queue = queue.Queue()


'''Waiting and resend functions'''

#This function takes type and source_id of the ack that is expected aswell as the message that may have to be resend and the adress to which it may have to be resend.
#We are waiting for 3s to get the correct ack an store all different messages that are arriving in that time. They will be put back on the queue to be treated later.																									---------------------------HHHIIIIEEEEEERRRRRRRRR-----------------------
def wait_for_acknowledgement(types, source_id, resend_data, addr):
	global waiting_flag
	waiting_flag = True
	wrong_messages = []
	#we try 3 times before giving up
	for i in range(3):
		#call waiter function
		status, wrong_messages = waiter(types, source_id, wrong_messages, (i+1))

		if status == 'received':
			return

		#resend the message (3 times)
		print('resend')
		UDPSock.sendto(resend_data, addr)
	print('could not send data')
	#if we did not receive the ack we also reset the queue and return
	waiting_flag = False

	# empty the waiting queue if there are still elements in there
	while waiting_queue.empty() == False:
		input = waiting_queue.get(block=False)
		wrong_messages.append(input)

	# put all the messages back in the normal queue
	for wrong_message in wrong_messages:
		messages_queue.put_nowait(wrong_message)
	return


def waiter(types, source_id, wrong_messages, timer):
	global waiting_flag
	# 0.5s from now
	timeout = time.time() + 0.5*timer
	# get messages from waiting queue
	while True:

		# if time passed we break the while loop
		if time.time() > timeout:
			status = 'resend'
			return (status, wrong_messages)
		try:
			input = waiting_queue.get(block=False)
			received_data, received_addr = input.data, input.address

		except:
			continue

		header = m.unpack_header(received_data)

		receiver_type = header['type']
		receiver_source_id = header['sourceID']
		A = header['A']

		# if we received the correct ack, pack wrong messages back in the queue and return
		if receiver_type in types and receiver_source_id == source_id:
			# stop input in the waiting queue
			waiting_flag = False
			print('received ack')
			# empty the waiting queue if there are still elemnts in there
			while not waiting_queue.empty():
				input = waiting_queue.get(block=False)
				wrong_messages.append(input)

			# put all the messages back in the actual queue
			for wrong_message in wrong_messages:
				messages_queue.put_nowait(wrong_message)

			status = 'received'
			return(status, wrong_messages)

		# pack wrong message in the wrong messages list
		else:
			wrong_message = Message(received_data, received_addr)
			wrong_messages.append(wrong_message)



''' functions for list administration '''

#checks if username is already in the list. returns True if username is ok and false if there is already somebody using it
def check_username(username):
	for id, client in clients.items():
		if client.username == username:
			return False
	return True


# add client to clients list
def connect_client(addr, username):
	# add client to clients dict
	global next_client_id
	client_id = next_client_id
	next_client_id += 1

	client = User(client_id, username, c.PUBLIC_GROUP_ID, addr)
	clients[client_id] = client

	# add new client to public group
	groups[c.PUBLIC_GROUP_ID].members.append(client)

	print('Connected to a new client: \t', client)
	return client


# receive a coded message and send it to receivers list
def send_message(msg, group_id):
	global groups
	receivers = groups[group_id].members
	for client in receivers:
		UDPSock.sendto(msg, client.address)
		print("Sent msg to client " + str(client))
		wait_for_acknowledgement([c.TYPE_DATA_MESSAGE], client.id, msg, client.address)


# function to update the list of all users if somebody joined or changed status.
# Input is a dictionary of the users that changed
def update_user_list(updated_users):
	for id, client in clients.items():
		msg = m.createUpdateList(0, updated_users)
		UDPSock.sendto(msg, client.address)
		print('Sent UPDATE_LIST to user ' + str(id))
		wait_for_acknowledgement([c.TYPE_UPDATE_LIST], client.id, msg, client.address)
	return


#This function changes the group of a user.
#It takes care that a group dissolution will be initiated if only one user is left (except of course for the public group)
def change_group(user_id, new_group_id):
	#change groups on the server
	global clients
	global groups
	user = clients[user_id]
	old_group_id = user.group
	changed_users = {}

	groups[old_group_id].members.remove(user)
	groups[new_group_id].members.append(user)

	new_group = groups[new_group_id]
	old_group = groups[old_group_id]

	user.group = new_group.id

	# If only one user remains delete group and send a group dissolution,
	# put that guy in the public group an inform everybody about the changes.
	if len(old_group.members) == c.PUBLIC_GROUP_ID and old_group_id != c.PUBLIC_GROUP_ID:

		#only member in the old group
		user_left = old_group.members[0]

		#send group dissolution
		msg = m.groupDissolution(0, old_group_id)
		UDPSock.sendto(msg, user_left.address)

		wait_for_acknowledgement([c.TYPE_GROUP_DISSOLUTION], user_left.id, msg, user_left.address)

		#delete old group in the group list
		del groups[old_group_id]

		#change group of old user to public group
		groups[c.PUBLIC_GROUP_ID].members.append(user_left)
		user_left.group=c.PUBLIC_GROUP_ID

		#update changes for everyone
		changed_users[user.id] = user
		changed_users[user_left.id] = user_left
		update_user_list(changed_users)

	else:
		changed_users[user.id] = user
		update_user_list(changed_users)




''' thread functions '''


def receive_data():
	while 1:
		# receive message
		data, addr = UDPSock.recvfrom(1024)
		if not data: break

		# put new message in the queue
		new_msg = Message(data, addr)
		if waiting_flag:
			waiting_queue.put_nowait(new_msg)
		else:
			messages_queue.put_nowait(new_msg)

def send_data():
	while 1:
		# try to get a message from the queue
		# if there's no message, try again without blocking
		try:
			input = messages_queue.get(block=False)
			data, addr = input.data, input.address
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

		# treat non-acknowledgement messages
		if msg_type == c.TYPE_CONNECTION_REQUEST:
			print(str(source_id) + ': CONNECTION_REQUEST')
			# get username from message content
			username = header['content'].decode().strip()
			#checks username and responses according to that check (allows or denies connection)
			if check_username(username) == True:
				if len(clients) < 250:
					# add client to clients list
					client = connect_client(addr, username)
					# send ConnectionAccept as response
					response = m.createConnectionAccept(0, client.id)
					UDPSock.sendto(response, client.address)
					print('sent CONNECTION_ACCEPT to client')

					# call waiting for ack function
					wait_for_acknowledgement([c.TYPE_CONNECTION_ACCEPT], client.id, response, client.address)

					# update list of other users
					updated_user = {client.id: client}
					update_user_list(updated_user)
				else:
					# send error code 0 for maximum of members on the server
					response = m.createConnectionReject(0,c.ERR0R_MAXIMUM_MEMBER_NUMBER)
					UDPSock.sendto(response, addr)
					# call waiting for ack function
					# client has no id yet so we are using the server id for him
					wait_for_acknowledgement([c.TYPE_CONNECTION_REJECT], c.SERVER_ID, response, addr)
			else:
				#send error code 1 for username already taken
				response = m.createConnectionReject(0,c.ERROR_USERNAME_ALREADY_TAKEN)
				UDPSock.sendto(response, addr)
				# call waiting for ack function

				wait_for_acknowledgement([c.TYPE_CONNECTION_REJECT], c.SERVER_ID, response, addr)

		elif msg_type == c.TYPE_DATA_MESSAGE:
			# send acknowledgement
			response = m.acknowledgement(msg_type, 0, c.SERVER_ID)       #Attention, all server acks have the source id 0
			UDPSock.sendto(response, addr)

			# get message text
			content = header['content']
			text = content[2:].decode()
			username = clients[source_id].username
			print("%s [%s]: %s" % (username, str(source_id), text))

			# resend it to users in same group
			send_message(data, group_id)

		elif msg_type == c.TYPE_USER_LIST_REQUEST:
			print(str(source_id) + ': USER_LIST_REQUEST')
			# send user list
			group_id = clients[source_id].group

			response = m.createUserListResponse(0, source_id, clients)
			print('send USER_LIST_REQUEST to client ' + str(source_id))
			UDPSock.sendto(response, clients[source_id].address)
			# call waiting for ack funtion
			wait_for_acknowledgement([c.TYPE_USER_LIST_RESPONSE], client.id, response, client.address)

		elif msg_type == c.TYPE_GROUP_INVITATION_ACCEPT:
			print(str(source_id) + ': GROUP_INVITATION_ACCEPT')
			group_type, group_id, member_id = \
				m.unpack_group_invitation_accept(data)

			#send ack for invitaion accept
			# send acknowledgement
			response = m.acknowledgement(msg_type, 0, c.SERVER_ID)  # Attention, all server acks have the source id 0
			UDPSock.sendto(response, addr)

			global group_invitations
			# if group doesn't exist, create it and add creator to it
			if group_id not in groups:

				# create new group
				new_group = Group(id=group_id, creator_id=source_id,
								  type=group_type, members=[])
				groups[group_id] = new_group

				# remove user from invitation list
				group_invitations[group_id].members.remove(member_id)

				# change creator to new group
				creator_id = groups[group_id].creator
				change_group(creator_id, group_id)

				# send an creation accept to creator
				msg = m.groupCreationAccept(0, creator_id,
											groups[group_id].type,
											group_id)
				UDPSock.sendto(msg, clients[creator_id].address)
				wait_for_acknowledgement([c.TYPE_GROUP_CREATION_ACCEPT], creator_id, msg, clients[creator_id].address)

			else:
				# remove user from invitation list
				group_invitations[group_id].members.remove(member_id)

				#delete invitation if everybody responded
			if len(group_invitations[group_id].members) == 0:
				del group_invitations[group_id]
				print('invitation has been deleted')

			#change group of member
			change_group(member_id, group_id)


			# will change user to public group to use the functionalities of the cahnge_group function and delete him after that.
		elif msg_type == c.TYPE_DISCONNECTION_REQUEST:
			print(str(source_id) + ': DISCONNECTION_REQUEST')

			#if client is not yet disconnected
			if source_id in clients.keys():

				#send acknowledgement
				#response = m.acknowledgement(msg_type, 0, 0x01)
				#UDPSock.sendto(response, addr)

				#change group to public group. Necessary because the function change_group takes care that there is more than one user in a group.
				client = clients[source_id]
				change_group(source_id, c.PUBLIC_GROUP_ID)


				# tell other clients that user disconnected
				update_disconnection = m.updateDisconnection(0, source_id)
				for id, client in clients.items():
					#if client.id != source_id:
					UDPSock.sendto(update_disconnection, client.address)
					wait_for_acknowledgement([c.TYPE_UPDATE_DISCONNECTION], client.id, update_disconnection, client.address)
					print('Sent UPDATE_DISCONNECTION to user ' + str(id))

				# remove client from group and client lists
				groups[c.PUBLIC_GROUP_ID].members.remove(client)
				del clients[source_id]
				pprint(clients)

			#if client is already disconnected but didn not receive the ack we are sending it again
			else:
				# send acknowledgement
				response = m.acknowledgement(msg_type, 0, c.SERVER_ID)
				UDPSock.sendto(response, addr)


		elif msg_type == c.TYPE_GROUP_CREATION_REQUEST:
			print(str(source_id) + ': GROUP_CREATION_REQUEST')
			group_type, members = m.unpack_group_creation_request(data)
			print("User %s is inviting members %s to a group of type %s"
				  % (source_id, members, group_type))

			ack = m.acknowledgement(c.TYPE_GROUP_CREATION_REQUEST, 0, c.SERVER_ID)  #TODO: server acks always have the source id 0. That has to be changed for other acks.
			UDPSock.sendto(ack,clients[source_id].address)

			# get an ID to new group
			group_id = next_group_id
			next_group_id += 1

			# add group to stand-by invitations dict
			group_invitations[group_id] = Group(id=group_id, creator_id=source_id,
												type=group_type, members=members)

			# invite members to group
			for id in members:
				invitation = m.groupInvitationRequest(0, source_id,
													  group_type, group_id,
													  id)
				UDPSock.sendto(invitation, clients[id].address)
				print('Sent GROUP_INVITATION_REQUEST to client ' + str(id))
				wait_for_acknowledgement([c.TYPE_GROUP_INVITATION_REQUEST], id, invitation, clients[id].address)

		elif msg_type == c.TYPE_GROUP_INVITATION_REJECT:
			print(str(source_id) + ': GROUP_INVITATION_REJECT')
			group_type, group_id, member_id = \
				m.unpack_group_invitation_accept(data)

			#delete this member in the group_invitation dict
			group_invitations[group_id].members.remove(member_id)

			# delete group from group_invitation dict if nobody accepted
			if len(group_invitations[group_id].members) == 0 and group_id not in groups:
				msg = m.groupInvitationReject(0, group_invitations[group_id].creator,                            # put flag 1 if last user rejected
										  group_invitations[group_id].type,
									  group_id, member_id, 1)
				del group_invitations[group_id]
				print('invitation has been deleted')

			else:
				msg = m.groupInvitationReject(0, group_invitations[group_id].creator,							# leave flag 0 if user that rejected was not the last one
											  group_invitations[group_id].type,
											  group_id, member_id)

			UDPSock.sendto(msg, clients[source_id].address)
			wait_for_acknowledgement([c.TYPE_GROUP_INVITATION_REJECT], source_id, msg, clients[source_id].address)

		elif msg_type == c.TYPE_GROUP_DISJOINT_REQUEST:
			# send acknowledgement
			response = m.acknowledgement(c.TYPE_GROUP_DISJOINT_REQUEST, 0, c.SERVER_ID)
			UDPSock.sendto(response, clients[source_id].address)

			#call change group
			change_group(source_id, c.PUBLIC_GROUP_ID)
			print(str(source_id) + ': DISJOINT GROUP')

			# send acknowledgement
			response = m.acknowledgement(msg_type, 0, source_id) # TODO: this acknowledgement really must use source_id?
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
