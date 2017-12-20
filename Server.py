import asyncore
import asynchat
import socket

PORT = 5005
NAME = 'TestChat'
class EndSession(Exception): pass


class CommandHandler:
	'''Std lib CMd '''
	def unknown(self, session, cmd):
		session.push("Unknown command: %s\r\n" %cmd)
	
	def handler(self, session, line):
		if not line.strip(): return
		parts = line.split(' ', 1)
		cmd = parts[0]
		try: line = parts[1].strip()
		except IndexError: line = ''
		meth = getattr(self, 'do_'+cmd, None)
		try: meth(session, line)
		except TypeError: self.unknown(session, cmd)

class Room(CommandHandler):
	'''Include all users, deal with cmd and broadcast '''

	def __init__(self, in_server):
		self.server = in_server
		self.sessions = []

	def add(self, session):
		self.sessions.append(session)

	def remove(self, session):
		self.sessions.remove(session)

	def broadcast(self, line):
		for session in self.sessions:
			session.push(line)

	def do_logout(self, session, line):
		raise EndSession

class LoginRoom(Room):
	'''Prepare new use a room'''
	
	def add(self, session):
		Room.add(self, session)
		self.broadcast('Welcome to %s\r\n' % self.server.name)

	def unknown(self, session, cmd):
		session.push('Please log in\nUse "login<Bob>"\r\n')

	def do_login(self, session, line):
		name = line.strip()
		if not name:
			session.push('Please enter a name\r\n')
		elif name in self.server.users:
			session.push('The name "%s" is already used.\r\n' %name)
			session.push('Please enter another name\r\n')
		else:
			session.name = name
			session.enter(self.server.main_room)

class ChatRoom(Room):
	#tell everyone a new user is now in
	def add(self, session):
		self.broadcast(session.name + ' has entered the room\r\n')
		self.server.users[session.name] = session
		Room.add(self, session)

	def remove(self, session):
		Room.remove(self, session)
		self.broadcast(session.name + ' has left the room\r\n')
	
	def do_say(self, session, line):
		self.broadcast(session.name + ': ' + line + '\r\n')
		
	def do_look(self, session, line):
		'''check who is in the room'''
		session.push('The following are in this room:\r\n')
		for other in self.sessions:
			session.push(other.name + '\r\n')
	
	def do_who(self, session, line):
		'''this deals with who command, check who logged in'''

		session.push('The following are logged in:\r\n')
		for name in self.server.users:
			session.push(name + "\r\n")

class LogoutRoom(Room):
		
	def add(self, session):
		try: del self.server.users[session.name]
		except KeyError: pass


		

class ChatSession(asynchat.async_chat):
	''' This is  class to connect server with users'''
	
	def __init__(self, sock):
		'''This is constructor of ChatSession, init its super calss async_chat and init the data with Null'''
		asynchat.async_chat.__init__(self, socket)
		self.set_terminator("\r\n")
		self.data = []
		self.name = None
		self.enter(LoginRoom(server))
		#Say hello to user :)
		#self.push('Welcome to %s\r\n' %self.server.name)	
	
	def enter(self, room):
		try: cur = self.room
		except AttributeError: pass
		else: cur.remove(self)
		self.room = room
		room.add(self)


	def collect_incoming_data(self, in_data):
		self.data.append(in_data)

	def found_terminator(self):
		'''If we find one terminator, we have read a whole message, share it with all users'''
		line = ''.join(self.data)
		#This is dealing the data incomming
		self.data=[]
		try: self.room.handle(self, line)
		except EndSession:
			#self.server.broadcast(line)
			self.handle_close()			

	def handle_close(self):
		'''A Wrapper function for handle_close()'''
		async_chat.handle_close(self)
		self.push("Bye!\r\n")
		self.server.disconnect(self)


class ChatServer(asyncore.dispatcher):
	'''Accept and connect individual user, intake broadcast'''
	def __init__(self, port, name):
		asyncore.dispatcher.__init__(self)
		#Note: we use STREAM  not  DGRAM
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(('', port))
		self.listen(5)
		self.name = name
		self.users = {}
		self.main_room = ChatRoom(self)


	def handle_accept(self):
		conn, addr = self.accept()
		self.sessions.append(ChatSession(conn))











	


#if we are in main
if __name__ == '__main__':
	ser = ChatServer(PORT, NAME)
	try: asyncore.loop()
	except KeyboardInterrupt: print
