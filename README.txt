RelayServer
===========

A service that that acts as a single proxy between many individual clients and 
many instances of a server. As both the clients and the servers are expected to 
initiate their connections to the relay server, this solution defeats NAT. This
platform is meant for an environment where the server (called the "host 
process") can actively hold many connections open to the relay server, but 
where the client connections will be intermittent.

Please note that this is a platform on which to build an application. The 
platform drives the application, whereby once the host process (HP) (your 
application) has successfully connected with the relay server and a client has 
successfully connected to the relay server, the client is assigned to a HP, 
your process will be sent all data received from the client. When a client 
connection drops, an announcement will be made and the assigned HP 
connection will be dropped. This will also happen in the reverse fashion. Any
HP connection whose assigned client connection has dropped, will be dropped.
The HP may make additional, new connections to the relay server at any time.

Connections are managed automatically. You need only fill the client and server 
with your logic, or build a new client and server that implement the same 
interface.
