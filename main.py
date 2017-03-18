import ctypes
import struct
import argparse

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

def generateFirstByte(headerType, R, S, A):
	return (headerType << 3) + (R << 2) + (S << 1) + A


#These are the functions to create the different packages that are defined in the protocol.

#Creates a connection request package. The inputs are the sequence number (that has to change after a unsuccessful try) and the username.
#Currently the function works only with a username that has exactly 8 bytes.
def createConnectionRequest(S, username):
	headerLength = 0x000D
	firstByte = generateFirstByte(TYPE_CONNECTION_REQUEST,0,S,0)
	username_filler = 8-len(username) #The field for the username consists of 8 byte. Should be used to at zeros if shorter. NOT IMPLEMENTED YET!!!!!!!
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH8s', buf, 0, firstByte, 0, 0, headerLength, username) #There might be a problem because in there is a "b" in front of the string in the example to indicate UTF-8. Can't use that here because its a variable and not a string like 'abc'.
	return buf

# Creates a connection accept. Inputs are the sequence number and the client ID
def createConnectionAccept(S, clientID):
	headerLength = 0x0006
	firstByte = generateFirstByte(TYPE_CONNECTION_ACCEPT,0,S,0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHB', buf, 0, firstByte, 0, 0, headerLength, clientID)
	return buf

#Creates a connection reject. Inputs are the sequence number and the error type (1 for "username already taken" 0 for "maximum numbers of users exceeded")
def createConnectionReject(S, errorType):
	headerLength = 0x0006
	firstByte = generateFirstByte(TYPE_CONNECTION_REJECT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBHB', buf, 0, firstByte, 0, 0, headerLength, errorType)
	return buf

#Creates a user list request. The input arguments are the sequence number an the source ID. The group ID is a fix value (0x01 for public group) since this message will be send immediately after the connection.
def createUserListRequest(S, sourceID):
	headerLength = 0x0005
	firstByte = generateFirstByte(TYPE_CONNECTION_REJECT, 0, S, 0)
	buf = ctypes.create_string_buffer(headerLength)
	struct.pack_into('>BBBH', buf, 0, firstByte, sourceID, 0x01, headerLength)
	return buf

def createUserListResponse(S, sourceID, )






	# Sender
	#buf = ctypes.create_string_buffer(7)
	# put data into the buffer
	#struct.pack_into('>B3sBH', buf, 0, 0b00000010, b'abc', 2, 455)

if __name__ == '__main__':
	pass
