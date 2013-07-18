#!/usr/bin/env python
import socket
import json

data = {'domains': [ { 'domain': 'pmm.johnbond.org'}, { 'domain': 'pmm2.jonbond.org'}] , 'data':'AABBCCDDEEFF'}

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('192.168.1.5', 9999))
#s.send("ouyouyouyo")
s.send(json.dumps(data))
result = json.loads(s.recv(1024))
print result
s.close()
