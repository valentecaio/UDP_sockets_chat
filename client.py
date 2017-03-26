# Echo client program
import socket
import threading
from time import sleep

import messages as m

try:
	from pprint import pprint
except:
	pprint = print

''' user commands '''
CMD_CONNECT = 'CONNECT'
CMD_SEND = 'SEND'
CMD_USER_LIST = 'USERS'
CMD_HELP = 'HELP'
CMD_DISCONNECT = 'DISCONNECT'
CMD_CREATE_GROUP = 'GCREATE'
CMD_ACCEPT_INVITATION = 'ACCEPT'

''' user states '''
ST_DISCONNECTED = 0
ST_CONNECTED = 1

''' global variables '''
address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
self_id = 0
self_group = 0
self_state = ST_DISCONNECTED
group_users = {}


''' thread functions '''


# used by user interface thread
def read_keyboard():
	global self_state
	print("Type messages to send: \t")
	while 1:
		user_input = input("")
		space = user_input.find(' ')
		user_cmd = (user_input[:space] if space is not -1 else user_input)
		print('command ' + user_cmd)

		if user_cmd == CMD_HELP:
			print(	'\t%s to show this help,\n'
				  	'\t%s to send a message,\n'
				  	'\t%s to connect to server\n'
					'\t%s to get the users list\n'
					'\t%s to disconnect\n'
				  % (CMD_HELP,CMD_SEND,CMD_CONNECT,CMD_USER_LIST, CMD_DISCONNECT))

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
				msg = m.createDataMessage(0, self_id, self_group, text)
				UDPsocket.sendto(msg, address_server)

			elif user_cmd == CMD_DISCONNECT:
				msg = m.disconnectionRequest(0, self_id)
				UDPsocket.sendto(msg, address_server)

			elif user_cmd == CMD_USER_LIST:
				pprint(group_users)

			elif user_cmd == CMD_CREATE_GROUP:
				args = user_input.split(' ')[1:]
				# removes spaces in the end
				if '' in args:
					args.remove('')

				# cast arguments to integers
				invalid_arg = False
				try:
					args = [int(arg) for arg in args]
				except:
					invalid_arg = True

				# verify if arguments are valid
				if (len(args) < 2) or (args[0] not in [0,1]) or invalid_arg:
					print("Usage:\n> %s <group type> <member 1> <member 2> ... "
						  "<member N>\nWhere <group type> must be 0 for "
						  "centralized or 1 for decentralized\n" % (CMD_CREATE_GROUP))
					continue

				# create request
				msg = m.groupCreationRequest(0, self_id, args[0], args[1:])
				UDPsocket.sendto(msg, address_server)

			else:
				print("This is not a valid command. Type "
					  + CMD_HELP + " to get some help.")
				continue

		#UDPsocket.sendto(msg, address_server)


# used by server listener thread
def main_loop():
	global self_group
	global group_users
	global self_id
	global self_state

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
				print('Received acknowledgement of type ' + str(msg_type))
				if msg_type == m.TYPE_USER_LIST_RESPONSE:
					pass
				# code enter here when receiving a userListResponse acknowledgement
				# elif ...
				if msg_type == m.TYPE_DISCONNECTION_REQUEST:
					#reset user data
					group_users.clear()
					self_group = 0
					self_id = 0
					print('You have been disconnected.')

			# treat non-acknowledgement messages
			else:
				if msg_type == m.TYPE_CONNECTION_ACCEPT:
					self_id = m.unpack_connection_accept_content(data)
					# the group id in that message is not the actual group
					# which will be 1 for public group after the connection
					self_group = 1

					print("Connected to group %s with id %s"
						  % (self_group, self_id))
					self_state = ST_CONNECTED

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
					source = group_users[source_id]
					username = source['username']
					print("%s [%s]: %s" % (username, str(source_id), text))

				elif msg_type == m.TYPE_USER_LIST_RESPONSE:
					group_users = m.unpack_user_list_response_content(data)

					print('received user list response')
					pprint(group_users)

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)

				elif msg_type == m.TYPE_UPDATE_LIST:
					changed_users = m.unpack_user_list_response_content(data)

					# update user list
					# user_list.update(changed_users)
					for id, client in changed_users.items():
						if id not in group_users:
							group_users[id] = client

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, self_id)
					UDPsocket.sendto(response, address_server)
					print('Changes in the user list. Type "USERS" to see changes')

				elif msg_type == m.TYPE_UPDATE_DISCONNECTION:
					self_id = m.unpack_connection_accept_content(data)

					username = group_users[header['clientID']]['username']
					del group_users[self_id]

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

					group_type_label = ('public' if group_type is 0 else 'private')
					print('User %s[%s] is inviting you to join a %s group\n'
						  'Type "%s %s" to join group'
						  % (group_users[source_id]['username'], source_id,
							 group_type_label, CMD_ACCEPT_INVITATION, group_id))

		except Exception as exc:
			# hide errors if disconnected
			if self_state is not ST_DISCONNECTED:
				print(exc)
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
