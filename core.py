class Message():
	def __init__(self, data, address):
		self.data = data
		self.address = address


class User():
	def __init__(self, id, username, group_id, address):
		self.id = id
		self.username = username
		self.group = group_id
		self.address = address
