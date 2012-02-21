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
import random
import threading
import time



def timeout_and_retry(lmbd, timeout = 0.1, retries = 100):
  """Try calling (XML RPC) function until it succeeds or run out of tries"""
  res = None
  def inf_gen():
    while True:
      yield -1
  retries_range = range(retries) if not retries is None else inf_gen
  socket.setdefaulttimeout(timeout)
  for i in retries_range:
    try:
      res = lmbd()
    except xmlrpclib.Fault:
      pass
    finally:
      socket.setdefaulttimeout(None)
      return res
  raise xmlrpclib.Fault('Failed after %i retries.' % retries);


class Neighbour():
  def __init__(self, name, capacity):
    self.name = name
    self.capacity = capacity

  def __str__(self):
    return '%s(%s)' % (self.name, self.capacity)

class Discover(threading.Thread):

  name = None
  capacity = 0
  neighbours = []
  host = ''
  port = None
  peers = []
  me = None

  action_queue = []

  def __init__(self, name, host, port, capacity):
    self.name = name
    self.host = host
    self.port = port
    self.capacity = capacity
    self.me = 'http://%s:%s' % (self.host, self.port)

  def _accept_neighbour(self, c0):
    if len(self.neighbours) >= self.capacity:
      return False
    return random.choice(True, False)

  def as_neighbour(self):
    return Neighbour(self.name, self.capacity)

  def neighbour_q(self, who, capacity):
    print 'neighbour_q: %s %s' % (who, capacity)
    return (True, self.name, self.capacity)
    answer = _accept_neighbour(capacity)
    return (answer, self.name, self.capacity)

  def ping(self, who = None):
    print 'ping: %s' % who
    if not who is None and not who in self.peers and who != self.me:
      self.action_queue.append(('ping', who))
    return True
  
  def pong(self, who = None):
    print 'pong %s' % who
    if who != self.me:
      self.peers.append(who)
      self.action_queue.append(('neighbour?', who))
    return True

  def hello(self, known_address = None):
    print 'hello'
    server = xmlrpclib.Server(known_address)
    timeout_and_retry(
        lambda: server.ping('http://%s:%s' % (self.host, self.port)))
    return True

  def plist(self):
    print 'plist'
    return self.peers
  
  def nlist(self):
    print 'nlist'
    return self.neighbours
  
  def send_messages(self):
    while True:
      if self.action_queue:
        try:
          action = self.action_queue[0]
          if action[0] == 'ping':
            who = action[1]
            self.peers.append(who)
            server = xmlrpclib.Server(who)
            timeout_and_retry(
                lambda: server.pong('http://%s:%s' % (self.host, self.port)))
            for peer in self.peers:
              if peer != self.me and peer != who:
                server = xmlrpclib.Server(peer)
                timeout_and_retry(lambda: server.ping(who))
          elif action[0] == 'neighbour?':
            who = action[1]
            server = xmlrpclib.Server(who)
            answer_yn, neighbour_name, neighbout_capacity = timeout_and_retry(
                lambda: server.neighbour_q(
                    'http://%s:%s' % (self.host, self.port),
                    self.capacity))
            if answer_yn:
              self.neighbours.append(
                                     Neighbour(neighbour_name, neighbour_capacity))
        except:
          continue
        finally:
          self.action_queue = self.action_queue[1:]
      else:
        time.sleep(1)

  def serve(self, host = None, port = None):
    _host = host if not host is None else self.host
    _port = port if not port is None else self.port
    self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((_host, _port))
    self.server.register_function(self.hello, "hello")
    self.server.register_function(self.plist, "plist")
    self.server.register_function(self.ping, "ping")
    self.server.register_function(self.pong, "pong")
    self.server.register_function(self.nlist, "nlist")
    self.server.register_function(self.neighbour_q, "neighbour_q")
    self.server.register_function(self.as_neighbour, "as_neighbour")
    print 'Serving on: %s' % self.me
    self.server.serve_forever()


class Client():
  host = ''
  port = None
  server_address = None

  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.server_address = 'http://%s:%s' % (self.host, self.port)

  def hello(self, who):
    server = xmlrpclib.Server(self.server_address)
    timeout_and_retry(lambda: server.hello(who))

  def plist(self):
    server = xmlrpclib.Server(self.server_address)
    print timeout_and_retry(lambda: server.plist())

  def nlist(self, output_stream, given_peers):
    #remember to print our own neighbours
    server = xmlrpclib.Server(self.server_address)
    timeout_and_retry(lambda: server.plist())
    name = str(timeout_and_retry(lambda: server.as_neighbour()))
    neighbours = timeout_and_retry(lambda: server.nlist())
    nodes = {name: neighbours}
    for peer in given_peers:
      server = xmlrpclib.Server(self.server_address)
      peer_id = str(timeout_and_retry(lambda: server.as_neighbour()))
      nodes[peer_id] = timeout_and_retry(lambda: server.nlist())

    # Print graphviz
    print >> output_stream, 'graph network {'
    for peer in nodes:
      for neighbour in nodes[peer]:
        print >> output_stream, '"%s" -- "%s";' % (peer, neighbour)
    print >> output_stream, '}'

  def interactive(self):
    print 'Connected to: %s' % self.server_address
    while True:
      try:
        user_input = raw_input('> ')
        if user_input[:len('hello')] == 'hello':
          who = user_input[len('hello') + 1:]
          self.hello(who)
        elif 'plist' in user_input:
          self.plist()
        elif 'nlist' in user_input:
          args = user_input.split()
          output_stream = sys.stdout
          #either we should print to std.out or a file stream
          if len(args) > 1 and "-o" == args[-2]:
            filename = args[-1]
            output_stream = open(filename, 'w')
            args = args[:-2]
          given_peers = []
          if len(args) > 1:
            given_peers = args[1:]
          self.nlist(output_stream, given_peers)
        elif 'help' in user_input:
          print 'Available commands:'
          print ' hello PORT'
          print ' plist'
          print ' nlist'
        else:
          print 'Invalid command: %s' % user_input
      except (EOFError):
        # for terminal piping
        break


 #################################### Test ####################################

class TestDicovery():
  def testDiscovery(self, host = None, port = None, expected_set = None):
    known_address = 'http://%s:%s' % (host, port)
    actual_set = None
    while True:
      try:
        server = xmlrpclib.Server(known_address)
        actual_set = set(timeout_and_retry(lambda: server.plist()))
      except:
        continue
      finally:
        if(expected_set == actual_set):
          print (
              'Test succeeded for %s with discovery of %s peer(s)' %
              (known_address, len(actual_set)))
        else:
          print (
              'Test didn\'t succeed Expected set: %s actual set: %s' %
              (expected_set , actual_set))
        break

 #################################### Main ####################################

if __name__ == '__main__':
  if '--test' in sys.argv[1:]:
    port = int(sys.argv[2]) if len(sys.argv) > 2 else None
    host = sys.argv[3] if len(sys.argv) > 3 else None
    expected_set = set(json.loads(sys.argv[4]) if len(sys.argv) > 4 else '')
    TestDicovery().testDiscovery(host, port, expected_set)
  else:
    port = int(sys.argv[2]) if len(sys.argv) > 2 else None
    capacity = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    if '--interactive' in sys.argv[1:]:
      client = Client('localhost', port)
      client.interactive()
    else:
     threading.Thread(target = peer.serve).start()
     threading.Thread(target = peer.send_messages).start()
