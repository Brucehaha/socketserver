import optparse
import socket
import json
import struct
import os
import sys

STATUS_CODE = {
    250: "Invalid cmd format, e.g: {'action':'get','filename':'test.py','size':344}",
    251: "Invalid cmd ",
    252: "Invalid auth data",
    253: "Wrong username or password",
    254: "Passed authentication",
    800: "the file exist,but not enough ,is continue? ",
    801: "the file exist !",
    802: " ready to receive datas",
    900: "md5 valdate success"

}


class ClientHandler:
    def __init__(self):
        self.conn = socket.socket()
        self.current_path = None
        self.opt = optparse.OptionParser()
        self.opt.add_option('-P', '--port', dest='port')
        self.opt.add_option('-s', '--server', dest='server')
        self.opt.add_option('-p', '--password', dest='password')
        self.opt.add_option('-u', '--username', dest='username')
        self.options, self.args = self.opt.parse_args()
        # print('options', self.options)
        # print('args', self.args)
        self.verify_args()
        self.make_connection()
        self.main_path = os.path.dirname(os.path.abspath(__file__))

    def verify_args(self):
        pass

    def make_connection(self):
        self.conn.connect((self.options.server, int(self.options.port)))

    def interactive(self):
        print('{:*^30}'.format('Begin interact with server'))
        if self.authenticate():
            while 1:
                cmd = input('[%s]>> '%self.current_path).strip()
                cmd_list = cmd.split()
                if hasattr(self, cmd_list[0]):
                    func = getattr(self, cmd_list[0])
                    func(*cmd_list)

    def authenticate(self):
        if self.options.password and self.options.username:

            return self.get_auth_result(self.options.username, self.options.password)

        else:
            username = input("username: ").strip()
            password = input("password: ").strip()
            return self.get_auth_result(username, password)

    def get_auth_result(self, unm, pwd):
        data = {
            'action': 'auth',
            'username': unm,
            'password': pwd
        }
        self.conn.send(json.dumps(data).encode('utf8'))
        response = self.get_response()
        print(STATUS_CODE[response.get("status_code")])
        if response.get("status_code") == 254:
            self.current_path = unm
            return True

    def get_response(self):
        response = self.conn.recv(1024)
        print(response)
        response = json.loads(response.decode('utf8'))
        return response

    def process_data(self, data):
        self.conn.send(json.dumps(data).encode('utf8'))
        length_tuple = self.conn.recv(4)
        data_size = struct.unpack('i', length_tuple)[0]  # 4 bytes due to struct, with not stick with after recv
        recv_size = 0
        recv_data = ""
        while recv_size < int(data_size):
            recv_data += self.conn.recv(1024).decode()
            recv_size = len(recv_data)
        else:
            print("cmd res received...", recv_size)
            return recv_data

    def ls(self, *args):
        data = {
            'action': 'ls',
        }
        print(self.process_data(data))

    def cd(self, *args):
        data = {
            'action': 'cd',
            'dirname': args[1]
        }
        self.current_path = self.process_data(data)

    def mkdir(self, *args):
        data = {
            'action': 'mkdir',
            'dirname': args[1]
        }
        print(self.process_data(data))

    def exit(self, *args):
        sys.exit()

    def put(self, *cmd_list):
        action, local_path, target_path = cmd_list
        file_path = os.path.join(self.main_path, local_path)
        if '/' in local_path:
            file_path = os.path.join(self.main_path, local_path.split('/'))
        file_name = os.path.basename(file_path)
        file_size = os.stat(local_path).st_size
        data = {
            'action':'put',
            'file_name': file_name,
            'file_size': file_size,
            'target_path':target_path
        }
        has_sent = 0
        self.conn.send(json.dumps(data).encode('utf8'))
        status_code = self.conn.recv(1024).decode('utf8')
        if status_code == '800':
            # file is incomplete
            choice = input("existing a file, continue downloading?[Y/N]").strip()
            if choice.upper() == 'Y':
                self.conn.sendall('Y'.encode('utf8'))
                size_existed = self.conn.recv(1024).decode('utf8')
                has_sent = int(size_existed)

            else:
                self.conn.sendall('N'.encode('utf8'))

        elif status_code == '801':
            # file exists
            return
        else:
            pass
        # start send file data
        f = open(local_path, 'rb')
        f.seek(has_sent)
        while has_sent < file_size:
            data = f.read(1024)
            self.conn.sendall(data)
            has_sent += len(data)

ch = ClientHandler()

ch.interactive()