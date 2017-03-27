# Echo client program
import socket
import threading
import traceback
from time import sleep

import messages as m

try:
	from pprint import pprint
except:
	pprint = print

''' user commands '''
CMD_PRINT = 'PRINT'
CMD_CONNECT = 'CONNECT'
CMD_SEND = 'SEND'
CMD_USER_LIST = 'USERS'
CMD_HELP = 'HELP'
CMD_DISCONNECT = 'DISCONNECT'
CMD_CREATE_GROUP = 'GCREATE'
CMD_ACCEPT_INVITATION = 'ACCEPT'
CMD_REJECT_INVITATION = 'REJECT'
CMD_DISJOINT = 'DISJOINT'

''' user states '''
ST_DISCONNECTED = 0
ST_CONNECTED = 1

''' global variables '''
address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
self_id = m.NOBODY_ID
self_state = ST_DISCONNECTED
self_group_type = m.GROUP_CENTRALIZED
users = {}
group_invitations = {}
own_group_invitation = {}


''' auxiliary functions '''


def getIntArgs(s):
	args = s.split(' ')[1:]
	# removes spaces in the end
	if '' in args:
		args.remove('')

	# cast arguments to integers
	invalid_arg = False
	try:
		args = [int(arg) for arg in args]
	except:
		invalid_arg = True

	return args, invalid_arg


''' thread functions '''


# used by user interface thread
def read_keyboard():
	global self_state
	global self_group_type
	global self_id
	global own_group_invitation

	help_msg =	'\t%s to show this help,\n' \
				'\t%s <text> to send a message,\n' \
				'\t%s to connect to server\n' \
				'\t%s to get the users list\n' \
				'\t%s <group type> <member_1 id>....<member_n id> ' \
				'to create a private group (0=centr. and 1=decentr.)\n' \
				'\t%s <group id> to accept the invitation of this group\n' \
				'\t%s <group id> to reject the invitation of this group\n' \
				'\t%s to leave private group and join the public group again\n' \
				'\t%s to disconnect\n' \
			  % (CMD_HELP,CMD_SEND,CMD_CONNECT,CMD_USER_LIST,
				 CMD_CREATE_GROUP, CMD_ACCEPT_INVITATION,
				 CMD_REJECT_INVITATION, CMD_DISJOINT, CMD_DISCONNECT)

	print(help_msg)
	print("Type messages to send: \t")

	while 1:
		try:
			user_input = input("> ")
			user_cmd = user_input.split(' ')[0]
			#print('command ' + user_cmd)

			if user_cmd == CMD_HELP:
				print(help_msg)
			elif user_cmd == CMD_PRINT:
				print("ID: %s, group: %s, state: %s, group_type: %s\n"
					  % (self_id, users[self_id]['group'], self_state, self_group_type))
				pprint(users)

			elif user_cmd == CMD_CONNECT:
				# abort if already connected
				if self_state is not ST_DISCONNECTED:
					print("You can't use this command because you're already connected")
					continue

				# abort if username is too long
				username = user_input[len(CMD_CONNECT) + 1:].strip()
				if len(username) > 8:
					print('Your username can not contain more than 8 characters. '
						  'Please choose another one.')
					continue

				msg = m.createConnectionRequest(0, username)
				UDPsocket.sendto(msg, address_server)

			else:
				# abort others commands if not connected
				if self_state is not ST_CONNECTED:
					print("You can't use this command because you're not connected")
					continue

				if user_cmd == CMD_SEND:
					text = user_input[len(CMD_SEND)+1:].encode('utf-8')
					msg = m.createDataMessage(0, self_id, users[self_id]['group'], text)
					if self_group_type is m.GROUP_CENTRALIZED:
						UDPsocket.sendto(msg, address_server)
					else: # decentralized group
						for _,user in users.items():
							if user['group'] == users[self_id]['group']:
								UDPsocket.sendto(msg, user['addr'])

				elif user_cmd == CMD_DISCONNECT:
					msg = m.disconnectionRequest(0, self_id)
					UDPsocket.sendto(msg, address_server)

				elif user_cmd == CMD_USER_LIST:
					pprint(users)

				elif user_cmd == CMD_ACCEPT_INVITATION:
					args, invalid_arg = getIntArgs(user_input)

					group_id = args[0]
					# verify if arguments are valid
					if (len(args) < 1) or invalid_arg \
							or (group_id not in group_invitations):
						print("Usage:\n> %s <group id>\n"
							  "Where <group id> must be a valid id" % (user_input))
						continue


					sender_id = group_invitations[group_id]['creator']
					# create acceptation message and send it
					self_group_type = group_invitations[group_id]['type']
					accept = m.groupInvitationAccept(0, sender_id, self_group_type,
													 group_id, self_id)
					UDPsocket.sendto(accept, address_server)
					del group_invitations[group_id]

				elif user_cmd == CMD_REJECT_INVITATION:
					args, invalid_arg = getIntArgs(user_input)
					group_id = args[0]
					# verify if arguments are valid
					if (len(args) < 1) or invalid_arg \
							or (group_id not in group_invitations):
						print("Usage:\n> %s <group id>\n"
							  "Where <group id> must be a valid id" % (user_input))
						continue

					# create rejection message and send it
					sender_id = group_invitations[group_id]['creator']
					group_type = group_invitations[group_id]['type']
					reject = m.groupInvitationReject(0,sender_id, group_type,
													 group_id, self_id)
					UDPsocket.sendto(reject, address_server)
					del group_invitations[group_id]

				elif user_cmd == CMD_CREATE_GROUP:
					args, invalid_arg = getIntArgs(user_input)

					# verify if arguments are valid
					if (len(args) < 2) or (args[0] not in [0,1]) or invalid_arg:
						print("Usage:\n> %s <group type> <member 1> <member 2> ... "
							  "<member N>\nWhere <group type> must be 0 for "
							  "centralized or 1 for decentralized\n" % (user_input))
						continue

					own_group_invitation = {'type': args[0], 'members': args[1:]}

					# create request
					msg = m.groupCreationRequest(0, self_id, args[0], args[1:])
					UDPsocket.sendto(msg, address_server)

				elif user_cmd == CMD_DISJOINT:
					if users[self_id]['group'] == m.PUBLIC_GROUP_ID:
						print('You are already in the public group.')
					else:
						#send disjoint request
						disjoint_request = m.groupDisjointRequest(0, self_id)
						UDPsocket.sendto(disjoint_request, address_server)

				else:
					print("This is not a valid command. Type "
						  + CMD_HELP + " to get some help.")
					continue
		except:
			# hide errors if disconnected
			if self_state is not ST_DISCONNECTED:
				print(traceback.format_exc())
			continue


# used by server listener thread
def main_loop():
	global users
	global self_id
	global self_state
	global group_invitations
	global self_group_type

	while 1:
		try:
			data, addr = UDPsocket.recvfrom(1024)

			# unpack header
			header = m.unpack_header(data)
			msg_type = header['type']
			source_id = header['sourceID']
			#pprint(header)

			# treat acknowledgement messages according to types
			if header['A']:
				#print('Received acknowledgement of type ' + str(msg_type))
				if msg_type == m.TYPE_DISCONNECTION_REQUEST:
					#reset user data
					users.clear()
					self_id = m.NOBODY_ID
					self_group_type = m.GROUP_CENTRALIZED
					self_state = ST_DISCONNECTED
					print('You have been disconnected.')
				if msg_type == m.TYPE_GROUP_DISJOINT_REQUEST:
					print('You left the private group.')
					# return to centralized group type
					self_group_type = m.GROUP_CENTRALIZED


			# treat non-acknowledgement messages
			else:
				if msg_type == m.TYPE_CONNECTION_ACCEPT:
					self_id = m.unpack_connection_accept_content(data)

					print("Connected to PUBLIC GROUP with id " + str(self_id))
					self_state = ST_CONNECTED

					# start in centralized mode
					self_group_type = m.GROUP_CENTRALIZED

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

					# send user list request
					# this message will only be send once after the connection
					response = m.createUserListRequest(0, self_id)
					UDPsocket.sendto(response, address_server)

				elif msg_type == m.TYPE_DATA_MESSAGE:
					content = header['content']
					text = content[2:].decode()
					source = users[source_id]
					username = source['username']
					print("%s [%s]: %s" % (username, str(source_id), text))

				elif msg_type == m.TYPE_GROUP_CREATION_ACCEPT:
					print("Your group was created.")

					# change to new group mode
					self_group_type = own_group_invitation['type']

					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

				elif msg_type == m.TYPE_USER_LIST_RESPONSE:
					users = m.unpack_user_list_response_content(data)

					print('Received user list response')
					pprint(users)

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

				elif msg_type == m.TYPE_UPDATE_LIST:
					changed_users = m.unpack_user_list_response_content(data)

					# update user list
					for id, client in changed_users.items():
						users[id] = client

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)
					print('Changes in the user list. Type "USERS" to see changes')

				elif msg_type == m.TYPE_UPDATE_DISCONNECTION:
					client_id = m.unpack_connection_accept_content(data)

					username = users[client_id]['username']
					del users[client_id]

					#send Acknowledgment
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

					print(username + '  disconnected.')

				# checks error code. not the best way but works for the two existing codes 0 and 1
				elif msg_type == m.TYPE_CONNECTION_REJECT:
					if m.unpack_error_type(data) == 0:
						print("We are sorry. But the server has exceeded it's maximum number of users")
					else:
						print('This username is already taken. Please choose another one.')

				elif msg_type == m.TYPE_GROUP_INVITATION_REQUEST:
					group_type, group_id, member_id = m.unpack_group_invitation_request(data)
					invitation = {}
					invitation['type']= group_type
					invitation['id']= group_id
					invitation['creator']= source_id
					# add invitation to invitations in stand-by
					group_invitations[group_id] = invitation

					# warn user about invitation
					group_type_label = ('public' if group_type is m.GROUP_CENTRALIZED else 'private')
					print('User %s[%s] is inviting you to join a %s group\n'
						  'Type "%s %s" to join group or "%s %s" to reject this invitation.'
						  % (users[source_id]['username'], source_id,
							 group_type_label, CMD_ACCEPT_INVITATION, group_id,
							 CMD_REJECT_INVITATION, group_id))

				elif msg_type == m.TYPE_GROUP_DISSOLUTION:
					print('Your group has been deleted because you were the only'
						  ' member left. You are now in the public group again.')

					# return to centralized group type
					self_group_type = m.GROUP_CENTRALIZED

					# send Acknowledgment
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

					# tell user that his invitation has been rejected
				elif msg_type == m.TYPE_GROUP_INVITATION_REJECT:
					username = users[source_id]['username']
					print('User ' + username + ' rejected your invitation.')
					if header['R']:
						print('We are sorry but nobody accepted your request.')
					# send Acknowledgment
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

		except Exception as exc:
			# hide errors if disconnected
			if self_state is not ST_DISCONNECTED:
				print(traceback.format_exc())
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
