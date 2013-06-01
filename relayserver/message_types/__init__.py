from relayserver.message_types.command_pb2 import Command
from relayserver.message_types.hello_pb2 import HostProcessHelloResponse, Hello

def build_msg_cmd_connopen(assigned_hp_session):
        
    command = Command()
    command.version = 1
    command.message_type = Command.CONNECTION_OPEN
    command.open_properties.assigned_to_session = assigned_hp_session

    return command

def build_msg_cmd_conndrop(assigned_hp_session):
                
    command = Command()
    command.version = 1
    command.message_type = Command.CONNECTION_DROP
    command.drop_properties.session_id = assigned_hp_session
    
    return command

def build_msg_data_hphelloresponse(session_id, relay_host, relay_port):

    response = HostProcessHelloResponse()
    response.session_id = session_id
    response.relay_host = relay_host
    response.relay_port = str(relay_port)

    return response

def build_msg_data_hphello():
    hello = Hello()
    hello.version = 1

    return hello
