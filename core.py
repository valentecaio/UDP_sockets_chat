import constants as c


class Message:
	def __init__(self, data, address):
		self.data = data
		self.address = address

	def __repr__(self):
		return "addr: %s, data: %s" % (self.address, self.data)


class User:
	def __init__(self, id, username, group_id, address):
		self.id = id
		self.username = username
		self.group = group_id
		self.address = address

	def __repr__(self):
		return "[id: %s, username: %s, group: %s, address: %s]" \
			   % (self.id, self.username, self.group, self.address)

	def __str__(self):
		return "%s [%s]" % (self.username, self.id)


class Group:
	def __init__(self, type=c.GROUP_CENTRALIZED, members=[],
				 id='No ID', creator_id='No creator'):
		self.id = id
		self.creator = creator_id
		self.type = type
		self.members = members

	def __repr__(self):
		if self.id == c.PUBLIC_GROUP_ID:
			type = 'PUBLIC'
		elif self.type == c.GROUP_CENTRALIZED:
			type = 'CENTRALIZED'
		else:
			type = 'DECENTRALIZED'

		return "[id: %s, creator: %s, type: %s, members: %s]" \
			   % (self.id, self.creator, type, self.members)
