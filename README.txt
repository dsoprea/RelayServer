RelayServer
===========

This is a service that that acts as a single proxy between many individual 
clients and many instances of a server. As both the clients and the servers are 
expected to initiate their connections to the relay server, this solution 
defeats NAT. This platform is meant for an environment where the server (called 
the "host process") can actively hold many connections open to the relay 
server, but where the client connections will be intermittent.

Please note that this is a platform on which to build an application. The 
platform drives the application, whereby once the "host process" (HP) (the 
server) has successfully connected with the relay server and a client has 
successfully connected to the relay server, the client is assigned to an HP, 
and your process will begin being sent data received from the client and the 
client will be sent data received from the HP. 


How to Run With Packaged Client/Server Examples
===============================================

Use the scripts in bin/. For information on parameters, run from bin/:

    ./relay -h
    ./client -h
    ./server -h

Using defaults, you can execute "./relay", "./client", and "./server" in any
order, and when all three are able to handshake, you'll be in business.

(This is an excellent opportunity to use Terminator 
(http://www.tenshu.net/p/terminator.html))

NOTE: Although, technically, you can run the components in any order, the 
      client and server will backoff further and further, for each failed 
      connection. If you don't want to wait for them to reattempt, run the
      relay, first. 

The default client and server are configured as the EchoClient and EchoServer
example implementations.

See the configuration section below for more information.


Requirements
============

Twisted (https://pypi.python.org/pypi/Twisted)
Protocol Buffers ("python-protobuf", under Ubuntu) 


Directory Structure
===================

artifacts
  Miscellaneous resources, such as the Protocol Buffer declaratives.
  
bin
  Utility scripts to launch the relay server and the currently-configured 
  client and server.

endpoints
  The main client and server communication adapters. These manage the 
  connections to the relay server, and forward the actual proxied data to the
  "real" client and servers (see below).

message_types
  The compiled Protocol Buffer definitions.

real
  The example client/servers, along with the standard interfaces for -any-
  client and server.


Examples
========

There are two example client/server reference implementations packages with
this project:

echo_client, echo_server: 

  Similar to a ping, the client will regularly send messages to the server, and
  the server will return them.

hv_client, hv_server:

  The client will manufacture larger messages that will be processed by the
  server. When the server sees the end of the message, it will return it. When 
  the client sees the end of the response, it will send a new message. It does 
  this until it's reached a certain quantity, then it closes its connection, 
  which causes the server's connection to be closed, and then new connections 
  are automatically established. The process then repeats.

  In the beginning, the size of the message and the quantity to be sent was
  random. Currently, they are set to constant amounts (the randrange() calls 
  are commented) so that we could gauge the performance of the operating 
  environment. Since we see this as being of more use to everyone, in general, 
  we have left it this way.
    

Configuration
=============

The only configuration exists within the parameters of the three utility 
scripts, and the config.py script.

By default, the client and server target a relay-server listening for data at 
tcp://localhost:8000 with a command-channel at tcp://localhost:8001. For 
different host/ports, execute any of the following from the bin/ directory to 
see help for parameters:
  
    ./relay -h
    ./client -h
    ./server -h

The config.py script simply must import the classes that will be used as the 
client and server:

  The server class must be imported/aliased as "EndpointServer" and implement
  the relayserver.real.ireal_server.IRealServer interface.

  The client class must be imported/aliased as "EndpointClient" and implement
  the relayserver.real.ireal_client.IRealClient interface.


Further Details
===============

When a client connection drops, an announcement will be made and the assigned 
HP connection will be dropped. This will also happen in the reverse fashion. 
Any HP connection whose assigned client connection has dropped, will be 
dropped. The HP may make additional, new connections to the relay server at any 
time.

Connections are managed automatically. By default, (10) connections are created
from the server to wait for requests, and dropped connections from both the
server -and- the client are always replenished/reconnected. You need only 
implement a client and server for your purposes, and we'll take care of all 
connectivity.
 