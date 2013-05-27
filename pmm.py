#!/usr/bin/env python2
import SocketServer
import socket
import dns.resolver
import json
from pprint import pprint

class PoorMansMulticast(SocketServer.BaseRequestHandler):
    """
    """
    #this actully passes targets as a sort of reference
    #bit confusing if you ask me
    #http://stackoverflow.com/questions/986006/python-how-do-i-pass-a-variable-by-reference
    def get_ips(self,domain,targets):
        """
        """
        try:
            dnsinfo =  socket.gethostbyname_ex(str(domain['domain']))
        except IOError, e:
            print("ERROR: %s reason: %s" % (domain, e))
            return False
        for ip in dnsinfo[2]:
            targets['targets'].append({'ip': ip, 'port': domain['port']})
        return True
    
    def echo(self,data,target):
        """
        """
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            send_socket.connect((target['ip'], target['port']))
            send_socket.send(data)
            send_socket.close()
        except socket.error, (value,message): 
            print "ERROR: Could not open socket: " + message 
        return data

    def get_jsondata(self,data):
        """
        """
        jsondata = False
        try:
            data = json.loads(data)
            jsondata = True
        except ValueError: 
            print ("ERROR: No json found: %s" % data)
        return jsondata, data
    def get_srv(self,srv,proto,domain):
        """
        """
        domains = { "domains": [] }
        dest_port = ""
        status = False
        try:
            answer = dns.resolver.query("_%s._%s.%s" % (srv,proto,domain), 'SRV') 
            for rrdata in answer:
                domains['domains'].append({ "domain": rrdata.target, "port": rrdata.port} )
                print domains
            status = True

        except dns.resolver.NXDOMAIN:
            print "ERROR: No SRV RR found for %s" % domain
            return status, domain
        except dns.resolver.Timeout:
            print "ERROR: Timed out resolving %s" % domain
            return status, domain
        except dns.exception.DNSException:
            print "ERROR: Unhandled exception"
            return status, domain
        return status, domains
        
    def handle(self):
        """
        """
        print "HERE: %s" % self.request[0]
        data = str(self.request[0]).strip()
        incoming = self.request[1]
        port = 9999
        targets = { "targets": [] }
        domains =   [{ 'domain': 'pmm.johnbond.org', 'port': port }, { 'domain': 'ripe.jonbond.org', 'port': port}] 

        jsondata, data = self.get_jsondata(data)
        if jsondata:
            domains = data["domains"]
            data = data['data']
        for domain in domains:
            status, srv_targets = self.get_srv("pmm","udp",domain['domain'])
            if status:
                for domain in srv_targets['domains']:
                    self.get_ips(domain,targets)
            else:
                self.get_ips(domain,targets)
        for target in targets['targets']:
            data = self.echo(data, target)
        incoming.sendto(json.dumps({"message": data }), self.client_address)
        self.request = []

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 9999
    server = SocketServer.UDPServer((HOST, PORT), PoorMansMulticast)
    server.serve_forever()
