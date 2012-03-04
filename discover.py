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


def timeout_and_retry(lmbd, timeout = None, retries = 10):
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
    except xmlrpclib.Fault as f:
      print f
      if (f.faultCode != 1):
        pass
    else:
      socket.setdefaulttimeout(None)
      return res
  socket.setdefaulttimeout(None)
  raise xmlrpclib.Fault(-32300, 'Failed after %i retries.' % retries);

class Peer(object):
  def __init__(
      self,
      name = None, host = None, port = None, capacity = None,
      from_dict = None):
    self.name = name
    self.host = host
    self.port = port
    self.capacity = capacity
    if not from_dict is None:
      self.__dict__.update(from_dict)

  def uri(self):
    return 'http://%s:%s' % (self.host, self.port)

  def __repr__(self):
    return '%s(%s)' % (self.name, self.capacity)

  def __eq__(self, other):
    return (
      self.name == other.name and
      self.host == other.host and
      self.port == other.port and
      self.capacity == other.capacity)


class Discover(threading.Thread):
  """A peer-to-peer node"""
  peer_info = None
  neighbours = []
  peers = {}
  msgs_received = {}
  files = {}
  action_queue = []

  def __init__(self, name, host, port, capacity):
    self.peer_info = Peer(name, host, port, capacity)
    self.files[random.choice(('bacon', 'cheese', 'salad','tea','rice','cow','beer','wine','candy',
      'sugar','apple','orange','icecream','banana','cucumber','carrot','pineapple'))] = 'Nice recipe'

  def who(self):
    return self.peer_info

  def _accept_neighbour(self, c0):
    """Neighbour request decision function"""
    if len(self.neighbours) >= self.peer_info.capacity:
      return False
    return random.choice((True, False))

  def neighbour_q(self, who_info_dict):
    who = Peer(from_dict = who_info_dict)
    print 'neighbour_q: %s' % (who)
    answer = self._accept_neighbour(capacity)
    if (answer == True):
      self.neighbours.append(who)
    return (answer, self.peer_info)

  def ping(self, who):
    peer = Peer(from_dict = who)
    print 'ping: %s %s' % (peer.uri(), self.peer_info.uri())
    if not who is None and not who['name'] in self.peers and peer.uri() != self.peer_info.uri():
      peer = Peer(from_dict = who)
      if peer != self.peer_info:
        print self.peer_info, self.peer_info.__dict__, peer, peer.__dict__
        self.action_queue.append(('ping', peer))
        # We should add them right away to prevent complete flodding
        #  while we are handling the pong.
        # Then we should just not assume too much about our peer list.
        # Perhaps sanitize/check the list once in a while..
        self.peers[peer.name] = peer
    return True
  
  def has_found_file(self,msg_id):
    return self.msgs_received[msg_id]

  def found(self, msg_id, file_holder):
    self.msgs_received[msg_id]
    self.msgs_received[msg_id] = (True,file_holder)
    return True 

  def get_nr_search_msg(self, msg_id):
    msgs_received = None
    if msg_id in self.msgs_received:
      msgs_received = self.msgs_received[msg_id][2]
    if msgs_received == None:
      msgs_received = 0
    return msgs_received

  def find(self, requesting_peer,msg_id, file_to_find, TTL, k_walkers = -1):
    if TTL <= 0:
      return False
    TTL = TTL - 1
    if msg_id not in self.msgs_received:
      self.msgs_received[msg_id] = (False,self.peer_info,1)
      if file_to_find in self.files:
        print 'Found file in: %s' % 'own files'
        if requesting_peer != self.peer_info.uri():
          self.action_queue.append(('found', msg_id, requesting_peer))
        return True
      else:
        if k_walkers != -1:
          for i in range(k_walkers):
            neighbour = random.choice(self.neighbours)
            self.action_queue.append(('find', neighbour.uri(), requesting_peer, msg_id, file_to_find, TTL, k_walkers))
        else:
          for neighbour in self.neighbours:
            self.action_queue.append(('find', neighbour.uri(), requesting_peer, msg_id, file_to_find, TTL, k_walkers))
    else:
      #If already received message count messages received 1 up
      old_values = self.msgs_received[msg_id]
      found_file, file_holder, msgs_received = old_values[0],old_values[1],old_values[2]+1
      self.msgs_received[msg_id] = (found_file,file_holder,msgs_received)
    return False

  def pong(self, who = None):
    print 'pong %s' % who
    peer = Peer(from_dict = who)
    if peer != self.peer_info and not who['name'] in self.peers:
      self.peers[peer.name] = peer
      self.action_queue.append(('neighbour?', peer))
    return True

  def hello(self, known_address = None):
    print 'hello %s' % known_address
    server = xmlrpclib.Server(known_address)
    timeout_and_retry(lambda: server.ping(self.peer_info))
    return True

  def plist(self):
    print 'plist'
    return self.peers.values()
  
  def nlist(self):
    print 'nlist'
    return self.neighbours
  
  def get(self, file_to_get):
    if file_to_get in self.files:
      return self.files[file_to_get]
    else:
      return 'I don\'t have that bloody file, kay?!'

  def do_actions(self):
    # TODO(cskau): add automatic idle, accounting actions
    while True:
      if self.action_queue:
        try:
          action = self.action_queue[0]
          if action[0] == 'ping':
            who = action[1]
            server = xmlrpclib.Server(who.uri())
            timeout_and_retry(lambda: server.pong(self.peer_info))
            for peer in self.peers.values():
              if peer != self.peer_info and peer != who:
                server = xmlrpclib.Server(peer.uri())
                timeout_and_retry(lambda: server.ping(who))
          elif action[0] == 'neighbour?':
            who = action[1]
            server = xmlrpclib.Server(who.uri())
            answer_yn, neighbour = timeout_and_retry(
                lambda: server.neighbour_q(self.peer_info))
            print 'Friends %s ? %s' % (who, answer_yn)
            if answer_yn:
              self.neighbours.append(Peer(from_dict = neighbour))
          elif action[0] == 'find':
            server = xmlrpclib.Server(action[1])
            requesting_peer,msg_id, file_to_find, TTL, k_walkers = action[2:7]
            timeout_and_retry(lambda: server.find(requesting_peer,msg_id, file_to_find, TTL, k_walkers))
          elif action[0] == 'found':
            print action
            server = xmlrpclib.Server(action[2])
            timeout_and_retry(lambda: server.found(action[1], self.peer_info.uri()))
        except xmlrpclib.Fault as f:
          print 'XMLRPC Fault: %s' % f
          continue
        else:
          self.action_queue = self.action_queue[1:]
      else:
        time.sleep(1)

  def serve(self):
    self.server = SimpleXMLRPCServer.SimpleXMLRPCServer(
        (self.peer_info.host, self.peer_info.port))
    self.server.register_function(self.hello, "hello")
    self.server.register_function(self.plist, "plist")
    self.server.register_function(self.ping, "ping")
    self.server.register_function(self.pong, "pong")
    self.server.register_function(self.nlist, "nlist")
    self.server.register_function(self.neighbour_q, "neighbour_q")
    self.server.register_function(self.find, "find")
    self.server.register_function(self.found, "found")
    self.server.register_function(self.has_found_file, "has_found_file")
    self.server.register_function(self.who, "who")
    self.server.register_function(self.get, "get")
    self.server.register_function(self.get_nr_search_msg, 'get_nr_search_msg')
    print 'Serving on: %s' % self.peer_info.uri()
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

  def plist(self, should_print = True):
    server = xmlrpclib.Server(self.server_address)
    plist = [Peer(from_dict=p) for p in timeout_and_retry(lambda: server.plist())]
    if should_print == True:
      print plist
    return plist

  def get(self, file_to_get, file_holder):
    server = xmlrpclib.Server(file_holder)
    print server.get(file_to_get)

  def find(self, file_to_find, TTL=4, k_walkers = -1):
    server = xmlrpclib.Server(self.server_address)
    msg_id = random.randint(0,100000000)
    file_holder = self.server_address
    found_file = timeout_and_retry(lambda: server.find(self.server_address,msg_id, file_to_find, TTL, k_walkers))
    if found_file == False:
      print 'Searching for file %s' % file_to_find
      for i in range(TTL):
        time.sleep(1)
        found_file, file_holder = timeout_and_retry(lambda: server.has_found_file(msg_id))[0:2] 
        if found_file == True:
          break
        else:
          print '.'   
    if found_file == True:
      print 'Found file at %s' % file_holder
    else:    
      print 'Didn\'t find file'
    msgs_received = 0
    for peer in self.plist(False):
      server = xmlrpclib.Server(peer.uri())
      msgs_received += timeout_and_retry(lambda: server.get_nr_search_msg(msg_id))

    print 'Messages used for this search: %s' % msgs_received
  
  def nlist(self, output_stream, given_peers):
    #remember to print our own neighbours
    server = xmlrpclib.Server(self.server_address)
    peer = Peer(from_dict = timeout_and_retry(lambda: server.who()))
    neighbours = timeout_and_retry(lambda: server.nlist())
    peers = {peer.name: peer}
    nodes = {peer.name: neighbours}

    server_peers = dict([
        (p['name'], Peer(from_dict = p))
        for p in timeout_and_retry(lambda: server.plist())])
    for peer_name in given_peers:
      server = xmlrpclib.Server(server_peers[peer_name].uri())
      peers[peer_name] = server_peers[peer_name]
      nodes[peer_name] = timeout_and_retry(lambda: server.nlist())

    # Print graphviz
    print >> output_stream, 'graph network {'
    for peer_name in nodes:
      print >> output_stream, '"%s";' % (peers[peer_name])
      for neighbour in nodes[peer_name]:
        neighbour_info = Peer(from_dict = neighbour)
        print >> output_stream, '"%s" -- "%s";' % (peers[peer_name], neighbour_info)
    print >> output_stream, '}'

  def interactive(self):
    print 'Connected to: %s' % self.server_address
    server = xmlrpclib.Server(self.server_address)
    peer = Peer(from_dict = timeout_and_retry(lambda: server.who()))
    while True:
      try:
        user_input = raw_input('%s> ' % peer.name)
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
            output_stream = open(filename, 'w', 0)
            args = args[:-2]
            print filename
          given_peers = []
          if len(args) > 1:
            given_peers = args[1:]
          self.nlist(output_stream, given_peers)  
        elif 'find' in user_input:
          args = user_input.split()
          if len(args) > 3:
            file_to_get, TTL, walkers = args[1], int(args[2]), int(args[3])
            self.find(file_to_get, TTL, walkers)
          elif len(args) > 2:
            file_to_get, TTL = args[1], int(args[2])
            self.find(file_to_get, TTL)
          else:
            file_to_get = args[1]
            self.find(file_to_get)
        elif 'get' in user_input:
          args = user_input.split()
          file_to_get, file_holder = args[1:]
          self.get(file_to_get, file_holder)
        elif 'help' in user_input:
          print 'Available commands:'
          print ' hello <PORT>'
          print ' plist'
          print ' nlist'
          print ' find'
          print ' get'
        else:
          print 'Invalid command: %s' % user_input
      except (EOFError):
        # for terminal piping
        print
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
      except xmlrpclib.Fault as f:
        print 'XMLRPC Fault: %s' % f
        continue
      else:
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
  elif len(sys.argv) > 2:
    port = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if '--interactive' in sys.argv[1:]:
      client = Client('localhost', port)
      client.interactive()
    else:
      name = sys.argv[1] if len(sys.argv) > 1 else None
      capacity = int(sys.argv[3]) if len(sys.argv) > 3 else 0
      node = Discover(name, 'localhost', port, capacity)
      threading.Thread(target = node.serve).start()
      threading.Thread(target = node.do_actions).start()
  else:
    print './discover.py [--test] [--interactive] [NAME] <PORT> <CAPACITY>'