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


class Discover():

  server_address = ''

  def __init__(self, server_address):
    self.server_address = server_address

  def meh(self):
    server = xmlrpclib.Server(self.server_address)
    server.examples.getStateName(41)


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
