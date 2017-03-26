import ctypes
import socket
import struct

try:
	from pprint import pprint
except:
	pprint = print

# type constants
TYPE_CONNECTION_REQUEST = 0x00
TYPE_CONNECTION_ACCEPT = 0x01
TYPE_CONNECTION_REJECT = 0x02
TYPE_USER_LIST_REQUEST = 0x03
TYPE_USER_LIST_RESPONSE = 0x04
TYPE_DATA_MESSAGE = 0x05
TYPE_GROUP_CREATION_REQUEST = 0x06
TYPE_GROUP_CREATION_ACCEPT = 0x07
TYPE_GROUP_CREATION_REJECT = 0x08
TYPE_GROUP_INVITATION_REQUEST = 0x09
TYPE_GROUP_INVITATION_ACCEPT = 0x0A
TYPE_GROUP_INVITATION_REJECT = 0x0B
TYPE_GROUP_DISJOINT_REQUEST = 0x0C
TYPE_GROUP_DISSOLUTION = 0x0D
TYPE_UPDATE_LIST = 0x0E
TYPE_UPDATE_DISCONNECTION = 0x0F
TYPE_DISCONNECTION_REQUEST = 0x10

GROUP_CENTRALIZED = 0
GROUP_DECENTRALIZED = 1

### internal functions ###

def generateFirstByte(headerType, R, S, A):
	return (headerType << 3) + (R << 2) + (S << 1) + A

# The field for the username consists of 8 byte. This function adds spaces which can't be part of an actual username.
def usernameWithPadding(username):
	username = username.ljust(8)
	return username

# This function removes the spaces that have been added for the transmission.
def usernameWithoutPadding(username):
	username = username.strip()
	return username


#These are the functions to create the different packages that are defined in the protocol.


#Creates a connection request package. The inputs are the sequence number (that has to change after a unsuccessful try) and the username.
#Currently the function works only with a username that has exactly 8 bytes.
def createConnectionRequest(S, username):
	# fixed data defined in the specification
	headerLength = 0x000D
	sourceID = 0
	groupId = 0
	firstByte = generateFirstByte(TYPE_CONNECTION_REQUEST,0,S,0)
	buf = ctypes.create_string_buffer(headerLength)
	packed_username = bytes(usernameWithPadding(username), 'utf8')															#solved string packing problem
	struct.pack_into('>BBBH8s', buf, 0, firstByte, sourceID, groupId, headerLength, packed_username) #ATTENTION!! disabeled filling function for the string to test!
	return buf


# Creates a connection accept. Inputs are the sequence number and the client ID
def createConnectionAccept(S, clientID):
	# fixed data defined in the specification
	headerLength = 0x0006
	sourceID = 0
	groupId = 0

	firstByte = generateFirstByte(TYPE_CONNECTION_ACCEPT,0,S,0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHB', buf, 0, firstByte, sourceID, groupId, headerLength, clientID)
	return buf


# Creates a connection reject.
# Inputs are the sequence number and the error type
# 1 for "username already taken", 0 for "maximum numbers of users exceeded"
def createConnectionReject(S, errorType):
	# fixed data defined in the specification
	headerLength = 0x0006
	sourceID = 0
	groupId = 0

	firstByte = generateFirstByte(TYPE_CONNECTION_REJECT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHB', buf, 0, firstByte, sourceID, groupId, headerLength, errorType)
	return buf


# Creates a user list request. The input arguments are the sequence number an the source ID.
# The group ID is a fix value (0x01 for public group) since this message will be send immediately after the connection.
def createUserListRequest(S, sourceID):
	# fixed data defined in the specification
	headerLength = 0x0005
	groupId = 0x01

	firstByte = generateFirstByte(TYPE_USER_LIST_REQUEST, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, groupId, headerLength)
	return buf


#This function creates the user list response. The inputs are the sequence number, the source ID and a list of lists of the user Data.
#Each element of these list will be another list containing the following Data in that order (username, client ID, Group ID, IP Adress, Port).
#Attention! Filling of usernames with less then 8 characters is not treated in that function!!!
def createUserListResponse(S, sourceID, userDictionary):
	groupId = 0x01

	headerLength = 0X005
	optionsLength = 16*len(userDictionary)

	firstByte = generateFirstByte(TYPE_USER_LIST_RESPONSE, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength + optionsLength)

	# Packing the first 5 bytes which are always given
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, groupId, headerLength)

	# Packing the last bytes which can change size
	counter=0
	for key in userDictionary:

		# Calculating the offset in byte.
		offset = (5+counter*16)

		# packing address so that it can be send (ip adress has to be converted to the format long)
		ip, port = userDictionary[key]['addr']
		ip_int = struct.unpack('>L', socket.inet_aton(ip))[0]

		packed_username = bytes(usernameWithPadding(userDictionary[key]['username']), 'utf8')
		client_id = userDictionary[key]['id']
		client_group = userDictionary[key]['group']

		struct.pack_into('>BB8sLH', buf, offset, client_id, client_group, packed_username, ip_int, port)

		counter += 1
	return buf


# This function builds the Header for a message.
# Different from create user list for example, the actual data we transmit is not put into the header.
# Maybe that function has to be changed to pack also the payload into the packet.
def createDataMessage(S, sourceID, groupID, data):
	headerLength=0x007
	dataLength = len(data)
	firstByte = generateFirstByte(TYPE_DATA_MESSAGE, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength + dataLength)
	struct.pack_into('>BBBHH' + str(dataLength) + 's', buf, 0, firstByte, sourceID, groupID, headerLength, dataLength, data)
	return buf


# creates a Group creation Request.
# The member list is a list of user IDs that should recieve an invitation.
# The communication type specifies if it is a centralized(0) or a decentralized(1) communication.
def groupCreationRequest(S, sourceID, communicationType, memberList):
	# group ID for that type of massage is 0 by default (see protocol specification)
	groupId = 0x00
	headerLength = 6 + len(memberList)
	firstByte = generateFirstByte(TYPE_GROUP_CREATION_REQUEST, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHB', buf, 0, firstByte, sourceID, groupId, headerLength, communicationType)

	for i in range(len(memberList)):
		offset = (6+i)
		struct.pack_into('>B', buf, offset, memberList[i])
	return buf


# The input groupID is not the 3rd byte in the message (which is again 0)
# because this message is not adressed to a group but to a user.
# The groupID is given in the optional part of the header to tell the client the ID of his group that now has been created.
def groupCreationAccept(S, sourceID, communicationType, groupID):
	headerLength = 0x007
	firstByte = generateFirstByte(TYPE_GROUP_CREATION_ACCEPT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHBB', buf, 0, firstByte, sourceID, 0, headerLength, communicationType, groupID)
	return buf


# Message from the server if group creation wasn't succesful because nobody accepted.
def groupCreationReject(S, sourceID):
	headerLength = 0x005
	groupID = 0
	firstByte = generateFirstByte(TYPE_CONNECTION_REJECT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, groupID, headerLength)
	return buf


# The input source ID specifies the member that sent the invitation.
# The inputs group ID and Client ID are in the optional part of the header.
# They are specifieng the group ID that will be used for the members that join the group an the member that has been invited.
def groupInvitationRequest(S, sourceID, communicationType, groupID, clientID):
	headerLength = 0x008 	# TODO: check this because spec says 0x007 but it can't be right ---> yep script is lying
	firstByte = generateFirstByte(TYPE_GROUP_INVITATION_REQUEST, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHBBB', buf, 0, firstByte, sourceID, 0, headerLength, communicationType, groupID, clientID)
	return buf


#Similar structure to the invitation. The sender is now the person that has been invited. That means the source ID changed.
# The last 3 inputs are the same as in the correspondig invitation.
def groupInvitationAccept(S,sourceID, communicationType, groupID, clientID):
	headerLength = 0x008 	# TODO: check this because spec says 0x007 but it can't be right  ---> yep script is lying
	firstByte = generateFirstByte(TYPE_GROUP_INVITATION_ACCEPT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHBBB', buf, 0, firstByte, sourceID, 0, headerLength, communicationType, groupID, clientID)
	return buf


#The structure is the same as for the invitation accept just with a different type declaration.
def groupInvitationReject(S,sourceID, communicationType, groupID, clientID):
	headerLength = 0x007
	firstByte = generateFirstByte(TYPE_GROUP_INVITATION_REJECT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHBBB', buf, 0, firstByte, sourceID, 0, headerLength, communicationType, groupID, clientID)
	return buf


# Demand to leave a private group and join the public group again. Only the minimum header length required.
def groupDisjointRequest(S, sourceID):
	headerLength = 0x005
	groupID = 0
	firstByte = generateFirstByte(TYPE_GROUP_DISJOINT_REQUEST, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, groupID, headerLength)
	return buf


# Sent by the server to the last remaining user in a group.
# After the acknowledgement the user will be placed again in the public group.
# There is no input for the sourceID because the message is send by the server.
def groupDissolution(S, groupID):
	headerLength = 0x005
	userID = 0
	firstByte = generateFirstByte(TYPE_GROUP_DISSOLUTION, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, userID, groupID, headerLength)
	return buf

# message to update list of users (disconnections are treated seperately).
# updated users is a dictionary of the users that should be updated.)

def createUpdateList(S, updated_users):
	#broadcast groupID
	groupId = 0xFF
	sourceID = 0x00
	headerLength = 0X005
	optionsLength = 16 * len(updated_users)

	firstByte = generateFirstByte(TYPE_UPDATE_LIST, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength + optionsLength)

	# Packing the first 5 bytes which are always given
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, groupId, headerLength)

	# Packing the last bytes which can change size
	counter = 0
	for key in updated_users:
		# Calculating the offset in byte.
		offset = (5 + counter * 16)

		# packing address so that it can be send (ip adress has to be converted to the format long)
		ip, port = updated_users[key]['addr']
		ip_int = struct.unpack('>L', socket.inet_aton(ip))[0]

		packed_username = bytes(usernameWithPadding(updated_users[key]['username']), 'utf8')
		client_id = updated_users[key]['id']
		client_group = updated_users[key]['group']

		struct.pack_into('>BB8sLH', buf, offset, client_id, client_group, packed_username, ip_int, port)

		counter += 1
	return buf

# The server sends this message to all users using a broadcast group ID if another user left the channel.
# Since this message is sent by the server to all users
# The source ID is 0 and the group ID is 0xFFF which means that the broadcast address is used.
def updateDisconnection(S, clientID):
	headerLength = 0x006
	firstByte = generateFirstByte(TYPE_UPDATE_DISCONNECTION, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHB', buf, 0, firstByte, 0, 0xFF, headerLength, clientID)
	return buf


# Dissconnection request of a user.
# The source ID specifies the user that wants to deconnect.
def disconnectionRequest(S, sourceID):
	headerLength = 0x005
	firstByte = generateFirstByte(TYPE_DISCONNECTION_REQUEST, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, 0, headerLength)
	return buf


# The type of the message depends on the type of the message that demands an acknowledgement.
# The source ID can either be a user ID or 0 if the server sends the acknowledgement.
def acknowledgement(type, S, sourceID):
	headerLength = 0x005
	firstByte = generateFirstByte(type, 0, S, 1)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, 0, headerLength)
	return buf


''' pack and unpack functions '''

# content is the optinal header part of the message
# throws an error if trying to unpack messages without header
# This functions is called to identify a message. Some messages might require a special unpacking function after that
def unpack_header(msg):
	firstByte, sourceID, groupID, lenght, content \
		= struct.unpack_from(">BBBH" + str(len(msg) - 5) + "s",  msg, 0)
	type = firstByte >> 3
	R = firstByte >> 2 & 1
	S = firstByte >> 1 & 1
	A = firstByte & 1
	return {'A': A, 'S': S, 'R': R, 'type': type, 'sourceID': sourceID,
			'groupID': groupID, 'lenght': lenght, 'content': content}


# unpack function for the connection accept.
def unpack_connection_accept_content(msg):
	clientID = struct.unpack_from(">B", msg, 5)[0]
	return clientID


# unpack function for a data message if the length of the payload is needed
def unpack_data_message(msg):
	firstByte, sourceID, groupID, lenght, data_length, content\
		= struct.unpack_from(">BBBHH" + str(len(msg) - 7) + "s", msg, 0)
	type = firstByte >> 3
	R = firstByte >> 2 & 1
	S = firstByte >> 1 & 1
	A = firstByte & 1
	return {'A': A, 'S': S, R: 'R', 'type': type, 'sourceID': sourceID,
			'groupID': groupID, 'lenght': lenght, 'data_length': data_length, 'content': content}


# unpack user list in a dictionary
def unpack_user_list_response_content(msg):
	user_list = {}

	offset = 5
	while offset < len(msg):
		client_id, client_group, username, ip_int, port = struct.unpack_from(">BB8sLH", msg, offset)

		ip = socket.inet_ntoa(struct.pack('>L',ip_int))
		username = username.decode().strip()

		user = {'id': client_id, 'group': client_group,
				'username': username, 'ip':ip, 'port':port}
		user_list[client_id] = user

		offset += 16
	return user_list


# unpack group invitation request message
def unpack_group_invitation_request(msg):
	group_type, group_id, member_id = struct.unpack_from(">BBB", msg, 5)
	return group_type, group_id, member_id


# unpack group invitation accept message
def unpack_group_invitation_accept(msg):
	return unpack_group_invitation_request(msg)


#unpack error code of connection reject
def unpack_error_type(msg):
	firstByte, sourceID, groupID, lenght, error_code = struct.unpack_from(">BBBHB", msg, 0)
	type = firstByte >> 3
	R = firstByte >> 2 & 1
	S = firstByte >> 1 & 1
	A = firstByte & 1
	return error_code


# unpack group creation request
# returns the group type and the list of members IDs who may be invited
def unpack_group_creation_request(msg):
	user_list = []

	group_type = struct.unpack_from(">B", msg, 5)[0]

	offset = 6
	while offset < len(msg):
		memberID = struct.unpack_from(">B", msg, offset)[0]
		user_list.append(memberID)
		offset += 1
	print(str(group_type))
	return group_type, user_list


if __name__ == '__main__':
		pass


	### examples ###

	# Sender
	#buf = ctypes.create_string_buffer(7)
	# put data into the buffer
	#struct.pack_into('>B3sBH', buf, 0, 0b00000010, b'abc', 2, 455)
