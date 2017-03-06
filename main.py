from ctypes import create_string_buffer
import struct

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

def createHeader(headertype, sourceID=0, groupID=0):
	headerLenght = 0x0000
	if headertype is TYPE_CONNECTION_REQUEST:
		headerLenght = 0x000D
	elif headertype is TYPE_CONNECTION_ACCEPT:
		pass
	elif headertype is TYPE_CONNECTION_REJECT:
		pass

	buf = create_string_buffer(headerLenght)
	firstByte = generateFirstByte(TYPE_CONNECTION_REQUEST, 0, 0, 0)

	return struct.pack_into('BBBH', buf, 0, firstByte,
					 sourceID, groupID, headerLenght)

if __name__ == '__main__':
	pass
