#!/usr/bin/python

import time
import json
import urllib.parse
import http.client
from enum import Enum

DEBUG = False

class GuacError(Exception):
    def __init__(self, short_msg, http_response, msg):
        super().__init__('%s. httpCode: %d %s' % (short_msg, http_response.status, http_response.reason) + '\n' + msg.decode())

class PermissionsOperation(Enum):
    ADD = "add"
    REMOVE = "remove"

class SystemPermissions(Enum):
    ADMINISTER = "ADMINISTER"
    CREATE_USER = "CREATE_USER"
    CREATE_USER_GROUP = "CREATE_USER_GROUP"
    CREATE_CONNECTION = "CREATE_CONNECTION"
    CREATE_CONNECTION_GROUP = "CREATE_CONNECTION_GROUP"
    CREATE_SHARING_PROFILE = "CREATE_SHARING_PROFILE"

class ConnectionPermissions(Enum):
    READ = "READ"


class GuacamoleClient:

    def __init__(self, connection: "http.client.HTTPConnection | http.client.HTTPSConnection", path: str):
        self.connection = connection
        if not path.endswith('/'): path += '/'
        self.path = path
        self.token = ''
    
    def login(self, user: str, password: str):
        payload = urllib.parse.urlencode({'username' : user, 'password' : password})
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.connection.request("POST", self.path+"api/tokens", payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200: 
            raise GuacError("Login error", res, msg)
        response = json.loads(msg)
        self.token = response['authToken']

    def createGroup(self, groupName: str):
        newGroup = {
            "identifier": groupName,
            "attributes": {
                "disabled":""
            }
        }
        payload = json.dumps(newGroup)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("POST", self.path+"api/session/data/postgresql/userGroups?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error creating the group", res, msg)
    
    def _changeGroupPermissions(self, groupName: str, path: str, operation: PermissionsOperation, permissions: list[SystemPermissions]):
        l = []
        for permission in permissions:
            l.append({"op": operation.value, "path": path, "value": permission.value })
        payload = json.dumps(l)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("PATCH", self.path+"api/session/data/postgresql/userGroups/"+groupName+"/permissions?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error setting permissions for the group", res, msg)

    def changeGroupPermissions(self, groupName: str, operation: PermissionsOperation, permissions: list[SystemPermissions]): 
        self._changeGroupPermissions(groupName, "/systemPermissions", operation, permissions)
    
    def existsUser(self, userName: str) -> bool:
        payload = ''
        headers = {}
        self.connection.request("GET", self.path+"api/session/data/postgresql/users?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200: 
            raise GuacError("Error getting users", res, msg)
        response = json.loads(msg)
        return True if userName in response.keys() else False
        
    def getConnectionGroupId(self, connectionGroupName: str) -> "str | None":
        payload = ''
        headers = {}
        self.connection.request("GET", self.path+"api/session/data/postgresql/connectionGroups/ROOT/tree?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error getting connection groups", res, msg)
        response = json.loads(msg)
        for group in response['childConnectionGroups']:
            if group['name'] == connectionGroupName: 
                return group['identifier']
        return None

    def existsConnectionGroup(self, connectionGroupName: str) -> bool:
        return (self.getConnectionGroupId(connectionGroupName) != None)

    def createUser(self, userName: str, password: str):
        newUser = {
            "username": userName,
            "password": password,
            "attributes": {
                "disabled":"",
                "expired":"",
                "access-window-start":"",
                "access-window-end":"",
                "valid-from":"",
                "valid-until":"",
                "timezone":None
            }
        }
        payload = json.dumps(newUser)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("POST", self.path+"api/session/data/postgresql/users?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error creating the user", res, msg)

    def deleteUser(self, userName: str):
        payload = ""
        headers = {}
        self.connection.request("DELETE", self.path+"api/session/data/postgresql/users/"+userName+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error deleting the user", res, msg)

    def changeUserPassword(self, userName: str, password: str):
        user = {
            "username": userName,
            "password": password,
            "attributes": {
                # "guac-email-address":None,
                # "guac-organizational-role":None,
                # "guac-full-name":None,
                "expired":"",
                "timezone":None,
                "access-window-start":"",
                # "guac-organization":None,
                "access-window-end":"",
                "disabled":"",
                "valid-until":"",
                "valid-from":""
            },
            # "lastActive":1636377547779
        }
        payload = json.dumps(user)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("PUT", self.path+"api/session/data/postgresql/users/"+userName+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error modifying the user", res, msg)
            
    def _changeUserPermissions(self, userName: str, path: str, operation: str, permission: str):
        permissions = [{"op": operation, "path": path, "value": permission }]
        payload = json.dumps(permissions)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("PATCH", self.path+"api/session/data/postgresql/users/"+userName+"/permissions?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error setting permissions for the user", res, msg)

    def changeUserPermissions(self, userName: str, operation: PermissionsOperation, permission: SystemPermissions): 
        self._changeUserPermissions(userName, "/systemPermissions", operation.value, permission.value)

    def changeUserAccessToConnection(self, userName: str, operation: PermissionsOperation, connectionId: str):
        self._changeUserPermissions(userName, "/connectionPermissions/"+connectionId, operation.value, ConnectionPermissions.READ.value)

    def createConnectionGroup(self, connectionGroupName: str):
        newConnectionGroup = {
            "parentIdentifier": "ROOT",
            "name": connectionGroupName,
            "type": "ORGANIZATIONAL",
            "attributes":{
                "max-connections":"",
                "max-connections-per-user":"",
                "enable-session-affinity":""
            }
        }
        payload = json.dumps(newConnectionGroup)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("POST", self.path+"api/session/data/postgresql/connectionGroups?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error creating the connection group for the user", res, msg)
            
    def deleteConnectionGroup(self, connectionGroupId: str):
        payload = ""
        headers = {}
        self.connection.request("DELETE", self.path+"api/session/data/postgresql/connectionGroups/"+connectionGroupId+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error deleting the connection group", res, msg)
            
    def createVncConnection(self, connectionName: str, connectionGroupId: str, guacd_hostname: str, vnc_host: str, vnc_port: str, vnc_password: str, 
                            sftp_user: "str | None" = None, sftp_password: "str | None" = None, sftp_port: str = "22", 
                            sftp_disable_download: bool = False, sftp_disable_upload: bool = False,
                            disable_clipboard_copy: bool = False, disable_clipboard_paste: bool = False):
        newConnection = {
            "name": connectionName,
            "parentIdentifier": connectionGroupId,
            "protocol": "vnc",

            "attributes": {
                "max-connections": "",
                "max-connections-per-user": "",

                "weight": "",
                "failover-only": "",

                "guacd-hostname": guacd_hostname,
                "guacd-port": 4822,
                "guacd-encryption": "",
            },
            "parameters": {
                "hostname": vnc_host,
                "port": vnc_port,

                "password": vnc_password,

                "read-only": "",
                "swap-red-blue": "",
                "cursor": "",
                "color-depth": "",
                "clipboard-encoding": "",
                
                "dest-port": "",
                "recording-exclude-output": "",
                "recording-exclude-mouse": "",
                "recording-include-keys": "",
                "create-recording-path": "",

                "enable-sftp": "false" if sftp_user is None else "true",
                "sftp-hostname": vnc_host,
                "sftp-port": sftp_port,
                "sftp-root-directory": "/",
                "sftp-username": sftp_user,
                "sftp-password": sftp_password if sftp_password != None else vnc_password,
                "sftp-server-alive-interval": "",
                "sftp-disable-download": "true" if sftp_disable_download else "",
                "sftp-disable-upload": "true" if sftp_disable_upload else "",

                "disable-copy": "true" if disable_clipboard_copy else "",    # disable copy from the remote clipboar
                "disable-paste": "true" if disable_clipboard_paste else "",  # disable paste into the remote clipboard

                "enable-audio": ""
            }
        }
        payload = json.dumps(newConnection)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("POST", self.path+"api/session/data/postgresql/connections?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error creating the connection", res, msg)
        response = json.loads(msg)
        return str(response['identifier'])

    def getConnectionId(self, connectionName: str, connectionGroupId: str = "ROOT") -> "str | None":
        payload = ''
        headers = {}
        self.connection.request("GET", self.path+"api/session/data/postgresql/connectionGroups/"+connectionGroupId+"/tree?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error getting connections", res, msg)
        response = json.loads(msg)
        for connection in response['childConnections']:
            if connection['name'] == connectionName: 
                return str(connection['identifier'])
        return None

    def deleteConnection(self, connectionId: str):
        payload = ""
        headers = {}
        self.connection.request("DELETE", self.path+"api/session/data/postgresql/connections/"+connectionId+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204: 
            raise GuacError("Error deleting the connection", res, msg)

    def getConnectionInactivityDays(self, connectionId: str) -> "int | None":
        payload = ''
        headers = {}
        self.connection.request("GET", self.path+"api/session/data/postgresql/connections/"+connectionId+"/history?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 200:
            raise GuacError("Error getting the connection", res, msg)
        response = json.loads(msg)
        if len(response) == 0:  # if never used yet
            return None
        LastCreatedConnectionHistoryEntry = response[0]  # let's assume the entries are sorted and the first is the last created
        endTimestamp = LastCreatedConnectionHistoryEntry['endDate']   # timestamp in miliseconds
        if endTimestamp is None:  # if currently being used
            return 0
        seconds = time.time() - endTimestamp/1000
        return int(seconds/60/60/24)
    
    