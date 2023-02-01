#!/usr/bin/python

import json
import urllib.parse
import http.client

DEBUG = False

class GuacError(Exception):
    def __init__(self, short_msg, http_response, msg):
        super().__init__('%s. httpCode: %d %s' % (short_msg, http_response.status, http_response.reason) + '\n' + msg.decode())

class GuacamoleClient:

    def __init__(self, connection: "http.client.HTTPConnection | http.client.HTTPSConnection", path: str):
        self.connection = connection
        if not path.endswith('/'): path += '/'
        self.path = path
        self.token = ''
    
    def login(self, user, password):
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

    def existsUser(self, userName):
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
        
    def getConnectionGroupId(self, connectionGroupName):
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

    def existsConnectionGroup(self, connectionGroupName):
        return (self.getConnectionGroupId(connectionGroupName) != None)

    def createUser(self, userName, password):
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

    def deleteUser(self, userName):
        payload = ""
        headers = {}
        self.connection.request("DELETE", self.path+"api/session/data/postgresql/users/"+userName+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error deleting the user", res, msg)

    def changePasswordToUser(self, userName, password):
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
            
    def createConnectionGroup(self, connectionGroupName):
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
            
    def deleteConnectionGroup(self, connectionGroupId):
        payload = ""
        headers = {}
        self.connection.request("DELETE", self.path+"api/session/data/postgresql/connectionGroups/"+connectionGroupId+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error deleting the connection group", res, msg)
            
    def changePermissionToUser(self, userName, operation, permissionName): 
        permissions = [{"op": operation, "path":"/systemPermissions", "value": permissionName }]
        payload = json.dumps(permissions)
        if DEBUG: print(payload)
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self.connection.request("PATCH", self.path+"api/session/data/postgresql/users/"+userName+"/permissions?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204:
            raise GuacError("Error setting permissions for the user", res, msg)
            
    def createVncConnection(self, connectionName, connectionGroupId, guacd_hostname, vnc_host, vnc_port, vnc_password, 
                            sftp_user = None, sftp_password = None, sftp_port = "22", sftp_disable_download = False, sftp_disable_upload = False,
                            disable_clipboard_copy = False, disable_clipboard_paste = False):
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

    def getConnectionId(self, connectionName, connectionGroupId = "ROOT"):
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

    def deleteConnection(self, connectionId):
        payload = ""
        headers = {}
        self.connection.request("DELETE", self.path+"api/session/data/postgresql/connections/"+connectionId+"?token="+self.token, payload, headers)
        res = self.connection.getresponse()
        httpStatusCode = res.status
        msg = res.read()  # whole response must be readed in order to do more requests using the same connection
        if httpStatusCode != 204: 
            raise GuacError("Error deleting the connection", res, msg)

