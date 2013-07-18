#!/usr/bin/env python2
import SocketServer
import socket
import dns.resolver
import json
import argparse
from pprint import pprint

class PoorMansMulticastServer(SocketServer.ThreadingUDPServer):
    """
    SocketServer.ThreadingUDPServer With extra argument domains

    Instance variables:
    
    - RequestHandlerClass
    - domains
    """
    def __init__(self,server_address,RequestHandlerClass,domains):
        SocketServer.ThreadingUDPServer.__init__(self,server_address,RequestHandlerClass)
        self.domains = domains

class PoorMansMulticastHanlder(SocketServer.BaseRequestHandler):
    """
    Handeler class 
    """

    #this actully passes targets as a sort of reference
    #bit confusing if you ask me
    #http://stackoverflow.com/questions/986006/python-how-do-i-pass-a-variable-by-reference
    def get_ips(self,domain,targets,messages):
        """
        Resolve domain and append all results to targets.
        targets is passed by reference (should probably cange this so it just returns new targets)
        same with messages.  but perhaps both of these should be classes.
        Dictionaries constructed as follows are appended to targets['targets']
        {
            'ip': ""
            'port': ""
        }

        messages is passed by refrence and used to store status messages to return to the client
        Dictionaries constructed as follows are appended to messages['messages'] 
        { 
            'message': {
                'type': ""
                'status': ""
                'domain': ""
                'data': ""
            }
        }

        return True/False
        """
        message_type = "RESOLVE_IP"
        message_status = ""
        message_text = ""
        try:
            dnsinfo =  socket.gethostbyname_ex(str(domain['domain']))
            message_status = "INFO"
            message_text = { 'ips': dnsinfo[2] }
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': str(domain['domain']), 'data': message_text }})
        except IOError, e:
            message_status = "ERROR"
            message_text = str(e)
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': str(domain['domain']), 'data': message_text }})
            return False
        for ip in dnsinfo[2]:
            targets['targets'].append({'ip': ip, 'port': domain['port']})
        return True
    
    def echo(self,data,target,messages):
        """
        Send data to target.  target is a dictionary constructed as follows 
        {
            'ip': ""
            'port': ""
        }
        messages is passed by refrence and used to store status messages to return to the client
        Dictionaries constructed as follows are appended to messages['messages'] 
        { 
            'message': {
                'type': ""
                'status': ""
                'domain': ""
                'data': ""
            }
        """
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        message_type = "SEND"
        message_status = ""
        message_text = ""
        try:
            send_socket.connect((target['ip'], target['port']))
            send_socket.send(data)
            send_socket.close()
            message_status = "INFO"
            message_text = data
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'target': target['ip'] , 'data': message_text }})
        except socket.error, (value,message): 
            message_status = "ERROR"
            message_text = message
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': str(domain['domain']), 'data': message_text }})

    def get_jsondata(self,data):
        """
        Try to convert data into a json object.  
        if sucessfull return the true and the json object
        else return false and data
        """
        jsondata = False
        try:
            data = json.loads(data)
            jsondata = True
        except ValueError: 
            print ("ERROR: No json found: %s" % data)
        return jsondata, data
    def get_srv(self,srv,proto,domain,messages):
        """
        Try to resolve _srv._proto._domain.  
        messages is passed by refrence and used to store status messages to return to the client
        Dictionaries constructed as follows are appended to messages['messages'] 
        { 
            'message': {
                'type': ""
                'status': ""
                'domain': ""
                'data': ""
            }
        }
        
        Return the status of the operation and a dictionary (empty on faliure) constructed as follows
        { 
            'domains':[ 
                { 
                    'domain': ""
                    'port': ""
            ]
        }
        """

        domains = { "domains": [] }
        dest_port = ""
        message_type = "RESOLVE_SRV"
        message_status = ""
        message_text = ""
        status = False
        try:
            answer = dns.resolver.query("_%s._%s.%s" % (srv,proto,domain), 'SRV') 
            message_status = "INFO"
            message_text = str(answer)
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': domain, 'data': message_text }})
            for rrdata in answer:
                domains['domains'].append({ "domain": rrdata.target, "port": rrdata.port} )
            status = True

        except dns.resolver.NXDOMAIN:
            message_status = "ERROR"
            message_text = " SRV RR NOT found for %s" % domain
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': domain, 'data': message_text }})
            return status, domains
        except dns.resolver.Timeout:
            message_status = "ERROR"
            message_text = "Timed out resolving %s" % domain
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': domain, 'data': message_text }})
            return status, domains
        except dns.exception.DNSException:
            message_status = "ERROR"
            message_text = "Unhandled exception"
            messages['messages'].append({'message': { 'type': message_type, 'status': message_status, 'domain': domain, 'data': message_text }})
            return status, domains
        return status, domains
        
    def handle(self):
        """
        RequestHandlerClass handle function
        handler listens for json datastreams 
        """
        data = str(self.request[0]).strip()
        incoming = self.request[1]
        targets = { "targets": [] }
        messages = { "messages": [] }
        jsondata, data = self.get_jsondata(data)
        if jsondata:
            self.server.domains = data["domains"]
            data = data['data']
        for domain in self.server.domains:
            status, srv_targets = self.get_srv("pmm","udp",domain['domain'],messages)
            if status:
                for domain in srv_targets['domains']:
                    self.get_ips(domain,targets,messages)
            else:
                self.get_ips(domain,targets,messages)
        for target in targets['targets']:
            message = self.echo(data, target,messages)
        incoming.sendto(json.dumps(messages), self.client_address)
def main():
    parser = argparse.ArgumentParser(description="Deployment script for atlas anchor")
    parser.add_argument('--listen', metavar="0.0.0.0:9999", default="0.0.0.0:9999", help='listen address:port for server port is optional')
    parser.add_argument('--domains', metavar="pmm.johnbond.org:9999[,ripe.jonbond.org:9999]", default="pmm.johnbond.org:9999", help='comma seperated list of domain:port pairs')
    args = parser.parse_args()
    domains = []
    for domain in args.domains.split(","):
        domain, port = domain.split(":")
        domains.append({'domain': domain, 'port':port})
    host, port = args.listen.split(":")
    server = PoorMansMulticastServer((host, int(port)), PoorMansMulticastHanlder, domains)
    server.serve_forever()
if __name__ == "__main__":
    main()
