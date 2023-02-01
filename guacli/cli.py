#!/usr/bin/python3

import os
import argparse
import http.client
from getpass import getpass
import urllib.parse
from datetime import datetime
import socket
import guacli.guacamoleClient as guac
from guacli import __version__ as version

DEBUG = False

def create_user_parser(create_subparsers):
    create_user_parser = create_subparsers.add_parser('user', help='Creates a user', 
        description='This operation creates a user in guacamole database and a private connection group with the same name of the user.',
        epilog='Example of use: \n'
            + os.path.basename(__file__)+' --url "https://example.com/guacamole" --user guacadmin create user james-smith')
    create_user_parser.add_argument('NEW_USER_NAME', type=str, help='Name of the user to create')
    create_user_parser.add_argument('--new-user-password', type=str, default='..........', 
                                    help='Password for the user to create. (if this parameter is not set, it will be interactively asked)')
    create_user_parser.add_argument('--can-create-connections', action='store_true', help='The user will be able to create connections.')

def create_user_and_private_connection_group(client, args, newUserPassword):
    newUserName = args.NEW_USER_NAME
    # if client.existsUser(newUserName):
    #     print('The user '+newUserName+' already exists. Changing the password')
    #     client.changePasswordToUser(newUserName, newUserPassword)
    # else:
    print('Creating user: '+newUserName)
    client.createUser(newUserName, newUserPassword)
    
    if args.can_create_connections:
        print('Adding permission to create connections')
        client.changePermissionToUser(newUserName, 'add', 'CREATE_CONNECTION')
        
    ret = client.existsConnectionGroup(newUserName)
    if ret: 
        print('The connection group for the user already exists.')
        exit(code=7)
    
    #NOTE: The connection group must be created by the user because only the creator (or an admin) can create connections in the group. 
    #      If a connection group is created by an admin, only admins will be able to create connections in it.

    print('Adding permission to create connection groups to the user')
    client.changePermissionToUser(newUserName, 'add', 'CREATE_CONNECTION_GROUP')
    
    adminToken = client.token   # save admin token
    print('Login with the user... ', end='')
    client.login(newUserName, newUserPassword)
    print('OK.')
    
    print('Creating connection group: '+newUserName)
    client.createConnectionGroup(newUserName)
    
    print('Removing permission to create connection groups')
    client.token = adminToken     # restore admin token
    client.changePermissionToUser(newUserName, 'remove', 'CREATE_CONNECTION_GROUP')
    

def delete_user_parser(create_subparsers):
    create_user_parser = create_subparsers.add_parser('user', help='Deletes a user.', 
        description='This operation deletes a user in guacamole database and the private connection group with the same name of the user.',
        epilog='Example of use: \n'
            + os.path.basename(__file__)+' --url "https://example.com/guacamole" --user guacadmin delete user james-smith')
    create_user_parser.add_argument('USER_TO_DELETE', type=str, help='Name of the user to delete')

def delete_user_and_private_connection_group(client, args):
    userToDelete = args.USER_TO_DELETE
    print('Deleting user: '+userToDelete)
    client.deleteUser(userToDelete)
    
    ret = client.getConnectionGroupId(userToDelete)
    if ret is None: 
        print('Connection group "'+userToDelete+'" not found.')
        exit(code=3)
    print('The ID of connection group "'+userToDelete+'" is '+ret+'.')
    connectionGroupId = ret

    print('Deleting connection group: '+str(connectionGroupId))
    client.deleteConnectionGroup(connectionGroupId)
    

def create_connection_parser(create_subparsers):
    create_connection_parser = create_subparsers.add_parser('connection', help='Creates a connection', 
        description='This operation creates a connection for localhost VNC service in the guacamole API-REST endpoint provided.',
        epilog='Example of use: \n'
                + os.path.basename(__file__)+' --url "https://example.com/guacamole" --user guacadmin create connection some-connection'
                                            +' --guacd-host 10.111.51.93 --vnc-password somePassword --sftp-user tensor --sftp-password somePassword2')
    create_connection_parser.add_argument('CONNECTION_NAME', type=str, help='Name for the new connection.')
    create_connection_parser.add_argument('--connection-group', type=str, default=None, 
                                          help='Optional name of the existing connection group where create the new connection. '
                                              +'If not provided, the root group will be used.')
    create_connection_parser.add_argument('--guacd-host', type=str, required=True,
                                          help='DNS name or IP of the guacd service host.')
    create_connection_parser.add_argument('--vnc-host', type=str, default='..........', 
                                          help='DNS name or IP of the destination host, the VNC server. If not provided, it will be the host running this command.')
    create_connection_parser.add_argument('--vnc-password', type=str, required=True)
    create_connection_parser.add_argument('--sftp-user', type=str, default='..........',
                                          help='User name for connecting to the sftp (or ssh) service running in the same host for file transference.'
                                              +'If not provided sftp connection will not be done (file transference disabled).')
    create_connection_parser.add_argument('--sftp-password', type=str, default='..........',
                                          help='Password for connecting to the sftp (or ssh) service.'
                                              +'If sftp-user provided, the password for the VNC service will be used also for sftp.')
    create_connection_parser.add_argument('--sftp-disable-file-uploads', action='store_true')
    create_connection_parser.add_argument('--sftp-disable-file-downloads', action='store_true')

    create_connection_parser.add_argument('--disable-clipboard-copy', action='store_true', help='Disable copy from the remote clipboard.')
    create_connection_parser.add_argument('--disable-clipboard-paste', action='store_true', help='Disable paste into the remote clipboard.')

def create_connection(client, args):
    if args.connection_group != None:
        ret = client.getConnectionGroupId(args.connection_group)
        if ret is None: 
            print('Connection group "'+args.connection_group+'" not found.')
            exit(code=2)
        print('The ID of connection group "'+args.connection_group+'" is '+ret+'.')
        connectionGroupId = ret
    else:
        print('Connection group not provided, using ROOT group.')
        connectionGroupId = 'ROOT'

    vnc_host = args.vnc_host
    if vnc_host == '..........':
        # obtain the IP of the host running this code
        vnc_host = socket.gethostbyname(socket.gethostname())
    vnc_port = "5900"
    sftp_port = "2222"
    sftp_user = args.sftp_user if args.sftp_user != '..........' else None
    sftp_password = args.sftp_password if args.sftp_password != '..........' else None

    print('Creating VNC connection for '+vnc_host+':'+vnc_port)
    connectionName = args.CONNECTION_NAME  # "pod-deployed-on-"+datetime.today().strftime('%Y-%m-%d-%H:%M:%S') if args.CONNECTION_NAME == 'date' else args.CONNECTION_NAME
    client.createVncConnection(connectionName, connectionGroupId, args.guacd_host, 
                             vnc_host, vnc_port, args.vnc_password, sftp_user, sftp_password, sftp_port,  
                             args.sftp_disable_file_downloads, args.sftp_disable_file_uploads,
                             args.disable_clipboard_copy, args.disable_clipboard_paste)
    

def delete_connection_parser(delete_subparsers):
    create_connection_parser = delete_subparsers.add_parser('connection', help='deletes a connection', 
        description='This operation deletes a connection in the guacamole API-REST endpoint provided.',
        epilog='Example of use: \n'
                + os.path.basename(__file__)+' --url "https://example.com/guacamole" --user guacadmin delete connection some-connection')
    create_connection_parser.add_argument('CONNECTION_NAME', type=str, 
                                          help='Name of the connection to delete.')
    create_connection_parser.add_argument('--connection-group', type=str, default=None, 
                                          help='Optional name of the conection group where the connection is. '
                                              +'If not provided, it will be deleted from the root group.')
    
def delete_connection(client, args):
    if args.connection_group != None:
        ret = client.getConnectionGroupId(args.connection_group)
        if ret is None: 
            print('Connection group "'+args.connection_group+'" not found.')
            exit(code=2)
        print('Id of connection group "'+args.connection_group+'" is '+ret+'.')
        connectionGroupId = ret
    else:
        print('Connection group not provided, using ROOT group.')
        connectionGroupId = 'ROOT'

    ret = client.getConnectionId(args.CONNECTION_NAME, connectionGroupId)
    if ret is None: 
        print('Connection "'+args.CONNECTION_NAME+'" not found in the connection group.')
        exit(code=2)
    print('Id of connection "'+args.CONNECTION_NAME+'" is '+ret+'.')
    connectionId = ret

    print('Deleting connection: ' + connectionId)
    client.deleteConnection(connectionId)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='Commands', dest='command')
    subparsers.required = True
    create_parser = subparsers.add_parser('create', help='Creates a resource')
    delete_parser = subparsers.add_parser('delete', help='Deletes a resource')

    # RESOURCES_LIST = ['user', 'connection']
    # GET_HELP_CMD = "Type of resource. Choices: %s" % ", ".join(RESOURCES_LIST)
    # create_parser.add_argument(metavar="<RESOURCE>", dest="resource_type", help=GET_HELP_CMD, choices=RESOURCES_LIST)
    create_subparsers = create_parser.add_subparsers(title='Resource', dest='resource')
    create_subparsers.required = True
    create_user_parser(create_subparsers)
    create_connection_parser(create_subparsers)

    delete_subparsers = delete_parser.add_subparsers(title='Resource', dest='resource')
    delete_subparsers.required = True
    delete_user_parser(delete_subparsers)
    delete_connection_parser(delete_subparsers)
    
    # Common arguments
    parser.add_argument('--version', action="version", version=version)
    parser.add_argument('--url', type=str, required=True, help='Guacamole endpoint URL. Example: "https://example.com/guacamole"')
    parser.add_argument('--user', type=str, required=True, help='User name for login into the Guacamole API-REST endpoint')
    parser.add_argument('--password', type=str, default='..........', 
                        help='Password for login into the Guacamole API-REST endpoint (you should have a user in guacamole database with a not empty password). ' 
                           + 'May be you can access to Guacamole web page using an OIDC account, in that case the password probably is not the same. '
                           + '(if this parameter is not set, it will be interactively asked)')
    parser.add_argument('--debug', action='store_true', help='Write debug details in the standard output')

    args = parser.parse_args()
    DEBUG = args.debug
    
    # Parse Common arguments
    url = urllib.parse.urlparse(args.url)
    port = url.port
    if url.scheme == 'http':
        if port == None: port = 80
        connection = http.client.HTTPConnection(url.hostname, port) 
    else:
        if port == None: port = 443
        connection = http.client.HTTPSConnection(url.hostname, port)

    loginUser = args.user
    loginPassword = args.password
    if loginPassword == '..........':
        loginPassword = getpass("Password for "+args.user+ " in Guacamole: ")

    newUserPassword = None
    if args.command == "create" and args.resource == "user":
        newUserPassword = args.new_user_password
        if newUserPassword == '..........':
            newUserPassword = getpass("Password for the new user "+args.NEW_USER_NAME+ ": ")

    client = guac.GuacamoleClient(connection, url.path)
    try:
        print('Connecting to '+args.url+ 'api/')
        client.login(loginUser, loginPassword)
        print('Login success.')

        if args.command == "create":
            if args.resource == "user":
                create_user_and_private_connection_group(client, args, newUserPassword)
            if args.resource == "connection": 
                create_connection(client, args)
        elif args.command == "delete":
            if args.resource == "user":
                delete_user_and_private_connection_group(client, args)
            if args.resource == "connection": 
                delete_connection(client, args)
        else:
            print('Not implemented command "' + args.command + '"')
            exit(code=1)

        print('Done.')
        exit(code=0)
    except guac.GuacError as e:
        print(e)
        exit(code=1)

if __name__ == "__main__":
    main()
