#!/usr/bin/env python
# coding: UTF-8

''' A peer, that can discover and list other peers.
Each peer is characterised by:
 - a short, unique name, eg. 'P1'
 - an address, ie. IP address and port number
 - a capacity denoting the maximum number of neighbours, suggested range 1-10
Your system should support the following interactive commands:
  hello [ip:port]
initiates discovery of other peers, possibly bootstrapping with the peer residing at ip:port
  plist
lists the pool of peers known to the local peer. 
Your peer info should include the maximum number of neighbours that peer can have.
To make life easier on yourselves, you should use XML-RPC for communication between peers.
'''

import sys
import unittest
import xmlrpclib
import SimpleXMLRPCServer
import threading;

class Interactor(threading.Thread):
  server = None;

  def __init__(self, server):
    threading.Thread.__init__ ( self )
    self.server = server
  
  def run(self):
    while True:
      user_input = raw_input('> ')
      if user_input[:len('hello')] == 'hello':
        self.server.hello("http://"+user_input[len('hello') + 1:])
      elif user_input == 'plist':
        self.server.plist()


class Discover(threading.Thread):

  name = None
  capacity = 0
  neighbours = []
  host = ''
  port = None
  peers = []

  def __init__(self, name, host, port, cap):
    threading.Thread.__init__ ( self )
    self.name = name
    self.host = host
    self.port = port
    self.capacity = cap

  def ping(self, who = None):
    print "isInPing with who " + who
    if not who in self.peers:
      #for peer in self.peers:
      # server = xmlrpclib.Server(peer)
      #  server.ping(who)
      self.peers.append(who)
    return True
  
  def pong(self, who = None):
    self.peers.append(who)
    print "isInPong";
    return True
  
  def hello(self, known_address = None):
    server = xmlrpclib.Server(known_address)
    #server.system.method_list()
    print "http://"+self.host+":"+str(self.port)
    if server.ping("http://"+self.host+":"+str(self.port)):
      self.pong(known_address)
    return True
  
  def plist(self):
    print("Capacity: " + str(self.capacity))
    print("Peer list:")
    for peer in self.peers:
      print(peer)
    return True
  
  def run(self):
    _host = self.host
    _port = self.port
    self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((_host, _port))
    self.server.register_function(self.hello, "hello")
    self.server.register_function(self.plist, "plist")
    self.server.register_function(self.ping, "ping")
    self.server.register_function(self.pong, "pong")
    print 'Now serving !'
    self.server.serve_forever()

 #################################### Test ####################################

class TestDicovery(unittest.TestCase):

  def setUp(self):
    None

  def test_true(self):
    self.assertEqual(True, True)


 #################################### Main ####################################

if __name__ == '__main__':
  if '--test' in sys.argv[1:]:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDicovery)
    unittest.TextTestRunner(verbosity=2).run(suite)
    exit(0)
  
  port = None
  cap = 0
  if len(sys.argv) > 2:
    port = int(sys.argv[2])
  if len(sys.argv) > 3:
    cap = int(sys.argv[3]);
  
  name = sys.argv[1]
  peer = Discover(name, 'localhost', port, cap);
  peer.start()
  Interactor(peer).start()
 
  
