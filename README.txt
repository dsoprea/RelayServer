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


How to Run With Packaged Server Example
=======================================

Use the scripts in bin/. For information on parameters, run from bin/:

    ./relay -h
    ./server -h

Using defaults, you can just execute "./relay" and "./server" in any order, and 
when they finally connect to each other, you'll be in business. Once these are
established, you can use something like "telnet" to test. The default port for
the client connections is (8002).

(This is an excellent opportunity to use Terminator 
(http://www.tenshu.net/p/terminator.html))

NOTE: Although, technically, you can run the components in any order, the 
      server will backoff further and further, for each failed connection. If 
      you don't want to wait for it to reattempt, run the relay, first. 

The default server is configured as the EchoServer example implementation.

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
  Utility scripts to launch the relay and the currently-configured server.

message_types
  The compiled Protocol Buffer definitions.

real
  The example servers, along with the standard interface for servers.


Examples
========

There is an "echo" server reference implementations packaged with this project.
    

Configuration
=============

The only configuration exists within the parameters of the two utility 
scripts, and the config.py script.

By default, the relay-server listens on the following ports:

tcp://localhost:8000    Server sends data here (server data).
tcp://localhost:8001    Relay announces connection changes here (server 
                        command-channel).
tcp://localhost:8002    Any client can connect here (client data).

For different host/ports, execute the following from the bin/ directory to see 
the help for parameters:
  
    ./relay -h
    ./server -h

The config.py script simply must import the class that will be used as the 
server. It must be imported/aliased as "EndpointServer" and implement the 
relayserver.real.ireal_server.IRealServer interface.


Further Details
===============

When a client connection drops, an announcement will be made and the assigned 
HP connection will be dropped. This will also happen in the reverse fashion. 
Any HP connection whose assigned client connection has dropped, will be 
dropped. The HP may make additional, new connections to the relay server at any 
time.

Connections are managed automatically. By default, (10) connections are created
from the server to wait for requests, and dropped connections from both the
server are always replenished/reconnected. You need only implement a server for 
your purposes, and we'll take care of the connectivity.
 