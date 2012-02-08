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
import socket
import json

def timeout_and_retry(lmbd, timeout = 1, retries = 10):
  """Try calling (XML RPC) function until it succeeds or run out of tries"""
  res = None
  socket.setdefaulttimeout(timeout)
  for i in range(retries):
    try:
      res = lmbd()
    except xmlrpclib.Fault:
      pass
    finally:
      socket.setdefaulttimeout(None)
      return res
  raise xmlrpclib.Fault('Failed after %i retries.' % retries);

class Discover():

  name = None
  capacity = 0
  neighbours = []
  host = ''
  port = None
  peers = []
  me = None

  action_queue = []

  def __init__(self, name, host, port, cap):
    self.name = name
    self.host = host
    self.port = port
    self.capacity = cap
    self.me = 'http://%s:%s' % (self.host, self.port)

  def ping(self, who = None):
    print 'ping: %s' % who
    if not who is None and not who in self.peers and who != self.me:
      self.action_queue.append(('ping', who))
    return True
  
  def pong(self, who = None):
    print 'pong %s' % who
    if who != self.me:
      self.peers.append(who)
    return True
  
  def hello(self, known_address = None):
    print 'hello'
    server = xmlrpclib.Server(known_address)
    timeout_and_retry(
        lambda:(server.ping('http://%s:%s' % (self.host, self.port))))
    return True
  
  def plist(self):
    return self.peers
  
  def serve(self, host = None, port = None):
    _host = host if not host is None else self.host
    _port = port if not port is None else self.port
    self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((_host, _port))
    self.server.timeout = 1
    self.server.register_function(self.hello, "hello")
    self.server.register_function(self.plist, "plist")
    self.server.register_function(self.ping, "ping")
    self.server.register_function(self.pong, "pong")
    print 'Serving on: %s' % self.me
    # instead of serve_forever, we stop to check our action queue every loop
    while True:
      self.server.handle_request()
      if self.action_queue:
        try:
          action = self.action_queue[0]
          if action[0] == 'ping':
            who = action[1]
            self.peers.append(who)
            server = xmlrpclib.Server(who)
            timeout_and_retry(lambda:server.pong('http://%s:%s' % (self.host, self.port)))
            for peer in self.peers:
              if peer != self.me and peer != who:
                server = xmlrpclib.Server(peer)
                timeout_and_retry(lambda:server.ping(who))
        except:
          continue
        finally:
          self.action_queue = self.action_queue[1:]

  def interactive(self):
    server_address = 'http://%s:%s' % (self.host, self.port)
    self.server = xmlrpclib.Server(server_address)
    print 'Connected to: %s' % server_address
    while True:
      try:
        user_input = raw_input('> ')
        if user_input[:len('hello')] == 'hello':
          self.server.hello(user_input[len('hello') + 1:])
        elif user_input == 'plist':
          print self.server.plist()
        else:
          print 'Invalid command: %s' % user_input
      except (EOFError):
        # for terminal piping
        break


 #################################### Test ####################################

class TestDicovery():
  def testDiscovery(self, host = None, port = None, expected_set = None):
    known_address = 'http://%s:%s' % (host, port)
    while True:
      try:
        server = xmlrpclib.Server(known_address)
        actual_set = set(timeout_and_retry(lambda:server.plist()))
      except:
        continue
      finally:
        if(expected_set == actual_set):
          print 'Test succeeded for %s with discovery of %s peer(s)' % (known_address, len(actual_set)) 
        else:
          print 'Test didn\'t succeed Expected set: %s actual list: %s' %(list , actual_set)
        break


 #################################### Main ####################################

if __name__ == '__main__':
  if '--test' in sys.argv[1:]:
    port = int(sys.argv[2]) if len(sys.argv) > 2 else None
    host = sys.argv[3] if len(sys.argv) > 3 else None
    expected_set = set(json.loads(sys.argv[4]) if len(sys.argv) > 4 else '')
    TestDicovery().testDiscovery(host, port, expected_set)
  else:
    name = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else None
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 0
  
    peer = Discover(name, 'localhost', port, cap)
  
    if '--interactive' in sys.argv[1:]:
      peer.interactive()
    else:
      peer.serve()
