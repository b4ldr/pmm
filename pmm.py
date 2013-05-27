#!/usr/bin/env python2
import SocketServer
import socket
import json
from pprint import pprint

class PoorMansMulticast(SocketServer.BaseRequestHandler):
    """
    """

    def process_json(self,data):
        """
        """
        data = json.loads(str(data).strip())
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response = {'domains': []}
        for domain in data["domains"]:
            try:
                dnsinfo =  socket.gethostbyname_ex(domain['domain'])
            except IOError, e:
                print("error %s reason: %s" % (domain['domain'], e))
                continue
            for ip in dnsinfo[2]:
                try:
                    send_socket.connect((str(ip), 53))
                    send_socket.send(json.dumps(data))
                    send_socket.close()
                except socket.error, (value,message): 
                    print "Could not open socket: " + message 
        send_socket.close()
        return data
    def handle(self):
        """
        """
        incoming = self.request[1]
        data = self.process_json(self.request[0])
        incoming.sendto(json.dumps(data['data']), self.client_address)

if __name__ == "__main__":
    HOST, PORT = "192.168.1.5", 9999
    server = SocketServer.UDPServer((HOST, PORT), PoorMansMulticast)
    server.serve_forever()
