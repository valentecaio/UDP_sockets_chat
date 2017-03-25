# Echo client program
import socket
import threading
from time import sleep

import messages as m

try:
	from pprint import pprint
except:
	pprint = print

address_server = ('localhost', 1212)
UDPsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
client_id = 0
client_group = 0
user_list = {}

''' user commands '''
CMD_CONNECT = 'CONNECT'
CMD_SEND = 'SEND'
CMD_USER_LIST = 'USERS'
CMD_HELP = 'HELP'
CMD_DISCONNECT = 'DISCONNECT'
''' thread functions '''


# used by user interface thread
def read_keyboard():
	print("Type messages to send: \t")
	while 1:
		user_input = input("")
		space = user_input.find(' ')
		user_cmd = (user_input[:space] if space is not -1 else user_input)
		print('command ' + user_cmd)

		if user_cmd == CMD_CONNECT:
			username = user_input[len(CMD_CONNECT) + 1:].strip()
			if len(username) <= 8:
				msg = m.createConnectionRequest(0, username)
				UDPsocket.sendto(msg, address_server)
			else:
				print('Your username can not contain more than 8 characters. Please choose another one.')
				continue

		elif user_cmd == CMD_SEND:
			text = user_input[len(CMD_SEND)+1:].encode('utf-8')
			msg = m.createDataMessage(0, client_id, client_group, text)
			UDPsocket.sendto(msg, address_server)

		elif user_cmd == CMD_DISCONNECT:
			msg = m.disconnectionRequest(0, client_id)
			UDPsocket.sendto(msg, address_server)


		elif user_cmd == CMD_USER_LIST:
			'''
			for keys, value in user_list.items():
				for under_key, under_value in value.items():
					print(under_key)
					print(under_value)
			'''
			pprint(user_list)

		elif user_cmd == CMD_HELP:
			print(	'\t%s to show this help,\n'
				  	'\t%s to send a message,\n'
				  	'\t%s to connect to server\n'
					'\t%s to get the users list\n'
					'\t%s to disconnect\n'

				  % (CMD_HELP,CMD_SEND,CMD_CONNECT,CMD_USER_LIST, CMD_DISCONNECT))

		else:
			print("This is not a valid command. Type "
				  + CMD_HELP + "to get some help.")
			continue

		#UDPsocket.sendto(msg, address_server)


# used by server listener thread
def main_loop():
	global client_group
	global user_list
	global client_id
	while 1:
		try:
			data, addr = UDPsocket.recvfrom(1024)

			# unpack header
			unpacked_data = m.unpack_protocol_header(data)
			msg_type = unpacked_data['type']

			# treat acknowledgement messages according to types
			if unpacked_data['A']:
				if msg_type == m.TYPE_USER_LIST_RESPONSE:
					pass
				# code enter here when receiving a userListResponse acknowledgement
				# elif ...
				if msg_type == m.TYPE_DISCONNECTION_REQUEST:
					#reset user data
					user_list.clear()
					client_group = 0
					client_id = 0
					print('You have been disconnected.')
			# treat non-acknowledgement messages
			else:
				if msg_type == m.TYPE_CONNECTION_ACCEPT:
					unpacked_data = m.unpack_connection_accept(data)
					client_id = int(unpacked_data['clientID'])
					client_group = 1										#the group id in that message is not the actual group (which will be 1 for public group after the connection). See specifications

					print("Connected to group %s with id %s"
						  % (client_group, client_id))

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, client_id)
					UDPsocket.sendto(response, address_server)

					# send user list request
					# this message will only be send once after the connection
					response = m.createUserListRequest(0, client_id)
					UDPsocket.sendto(response, address_server)

				if msg_type == m.TYPE_DATA_MESSAGE:
					content = unpacked_data['content']
					text = content[2:]
					print("%s: %s" % (user_list[str(unpacked_data['sourceID'])]['username'], text.decode()))

				if msg_type == m.TYPE_USER_LIST_RESPONSE:
					user_list = m.unpack_user_list_response(data)

					print('received user list response')
					pprint(user_list)

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, client_id)
					UDPsocket.sendto(response, address_server)

				if msg_type == m.TYPE_UPDATE_LIST:
					changed_users = m.unpack_user_list_response(data)
					user_list.update(changed_users)
					for id, client in changed_users.items():
						if id not in user_list:
							user_list[id] = client

					# send Acknowledgment as response
					response = m.acknowledgement(msg_type, 0, client_id)
					UDPsocket.sendto(response, address_server)
					print('Changes in the user list. Type "USERS" to see changes')

				if msg_type == m.TYPE_UPDATE_DISCONNECTION:
					unpacked_data = m.unpack_connection_accept(data)
					client_id = int(unpacked_data['clientID'])
					username = user_list[str(unpacked_data['clientID'])]['username']
					del user_list[str(client_id)]

					#send Acknowledgment
					response = m.acknowledgement(msg_type, 0, client_id)
					UDPsocket.sendto(response, address_server)

					print(username + '  disconnected.')

				#checks error code. not the best way but works for the two existing codes 0 and 1
				if msg_type == m.TYPE_CONNECTION_REJECT:
					if m.unpack_error_type(data) == m.TYPE_CONNECTION_REQUEST:
						print("We are sorry. But the server has exceeded it's maximum number of users")
					else:
						print('This username is already taken. Please choose another one.')





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
