from twisted.internet import task
from network_message import NetworkMessage
from file_manager import FileManager

from date_utils import DateUtil

class LoginServer():
    '''
        Login server creates new users, and manages storage and retrieval of user keys.
        
        Currently, both user private key and public key are stored on the server.
        
        User private key is encrypted with the user password.
        This means that the user private key can be attacked directly with brute-force attacks.
        TODO: this needs to be improved, because human-chosen passwords are usually much too weak.
    '''
    
    def __init__(self, network_path):
        self.network_path = network_path
        
    # called when a message is received from a client
    def receive_message(self, sender_client, message):
        if message.command == "CREATE":
            # check that the new user if not already existing
            if FileManager.file_exists(message.network_path):
                message.command = "USER_ALREADY_EXISTS"
                message.content = ""
                sender_client.send_message(message)
                return
            
            username, user_public_key, user_private_key = message.content
            creation_time = DateUtil.utcnow()
            
            FileManager.file_write(message.network_path, [username, creation_time, user_public_key, user_private_key])
            
            message.command = "USER_CREATED"
            message.content = username
            sender_client.send_message(message)
        
        elif message.command == "READ_USER_LOGIN_DATA":
            # check that the user exists
            if not FileManager.file_exists(message.network_path):
                message.command = "USER_NOT_EXISTING"
                message.content = ""
            else:
                # read all the information of a user
                message.command = "USER_LOGIN_DATA"
                message.content = FileManager.file_read(message.network_path)
            sender_client.send_message(message)
    
    # called when a client connection is lost
    def connection_lost(self, lost_client):
        # currently, nothing special to do
        pass
