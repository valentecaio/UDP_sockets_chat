import threading
from time import sleep

def wait():
	for i in range(9999):
		a = pow(i,99)

def listen():
	while 1:
		print("Press enter when you hear the sound.")
		wait()
		
def send():
	input('coe: ')
	wait()

thread_listen = threading.Thread(target=listen)
thread_listen.daemon = True
thread_listen.start()

thread_sender = threading.Thread(target=send)
thread_sender.daemon = True
thread_sender.start()

while 1:
	sleep(2)