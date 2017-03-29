import random
from socket import socket


class socerr(socket):

    def __init__(self, domain, transport, rate):
        self._sock = socket(domain, transport)
        self.error = rate

    def sendto(self, *p):
        test = random.randint(1, 100)
        if test > self.error:
            return self._sock.sendto(*p)
        else:
            print("** LOSS **")

    def recvfrom(self, *p):
        return self._sock.recvfrom(*p)

    def bind(self, addr):
        return self._sock.bind(addr)

    def fileno(self):
        return self._sock.fileno()
