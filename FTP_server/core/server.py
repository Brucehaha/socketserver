import socketserver
import json
import configparser
from conf import settings
import struct
import os


STATUS_CODE  = {
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


class ServerHandler(socketserver.BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ServerHandler, self).__init__(*args, **kwargs)
        self.user = None
        self.main_path = None

    def handle(self):
        while 1:
            conn = self.request
            # data = {'action':'auth', 'username'='', 'password}
            data = conn.recv(1024)
            if data:
                data = json.loads(data.decode('utf8'))
                if hasattr(self, data.get('action')):
                    func = getattr(self, data.get('action'))
                    func(**data)
                else:
                     print('invalid command')
            else:
                break

    def send_response(self, status_code):
        response = {'status_code': status_code}
        self.request.sendall(json.dumps(response).encode('utf8'))

    def auth(self, **data):
        if data.get('username') is None or data.get('password') is None:
            self.send_response(253)
        else:
            user = self.authenticate(data.get('username'), data.get('password'))
            if user is None:
                print("send1")
                self.send_response(253)
            else:
                self.user = user
                self.send_response(254)

    def authenticate(self, username, pwd):
        cfg = configparser.ConfigParser()
        cfg.read(settings.ACCOUNTS_PATH)
        if username in cfg.sections():
            password = cfg[username]['password']
            if password == pwd:
                self.user = username
                self.main_path = os.path.join(settings.BASE_DIR, 'home', self.user)
                print("auth pass!")
                return username

    def send_data(self, data):
        size = struct.pack('i', len(data))  # transfer size to 4 bytes
        print(len(size))
        self.request.send(size)
        self.request.sendall(data.encode('utf8'))

    def ls(self, **kargs):
        file_list = os.listdir(self.main_path)
        file_list = '\n'.join(file_list)
        self.send_data(file_list)

    def cd(self, **kargs):
        dirname = kargs.get('dirname')
        if dirname == '..':
            valid_path = os.path.join(settings.BASE_DIR, 'home', self.user)
            if self.main_path == valid_path:
                pass
            else:
                self.main_path = os.path.dirname(self.main_path)
        elif dirname in os.listdir(self.main_path):
            self.main_path = os.path.join(self.main_path, dirname)
        elif "/" in dirname:
            path = os.path.join(self.main_path, *dirname.split("/"))
            if os.path.isdir(path):
                self.main_path = path
        self.send_data(self.main_path)

    def mkdir(self, **kwargs):
        dirname = kwargs.get('dirname')
        dirpath = os.path.join(self.main_path, dirname)
        print(dirname)
        data = "Path created"
        print(self.main_path)
        if dirname not in os.listdir(self.main_path):
            if "/" in dirname:
                os.makedirs(dirpath)

            else:
                os.mkdir(dirpath)
                print('yes')
        else:
            data = "Path existed!"
        self.send_data(data)

    def put(self, **data):
        file_name = data.get('file_name')
        file_size = data.get('file_size')
        target_path = data.get('target_path')
        abs_path = os.path.join(self.main_path, target_path, file_name)
        # initial file received size
        has_received = 0
        if os.path.exists(abs_path):
            file_exist_size = os.stat(abs_path).st_size
            if file_exist_size < file_size:
                self.request.sendall('800'.encode('utf8'))
                choice = self.request.recv(1024).decode('utf8')
                if choice == 'Y':
                    self.request.sendall(str(file_exist_size).encode('utf8')) # send to client, seek the position
                    # mark the existing file size for appending the left data to file
                    has_received = file_exist_size
                    f = open(abs_path, 'ab')
                else:
                    f = open(abs_path, 'wb')
            else:
                print("file exists!")
                self.request.sendall('801'.encode('utf8'))
                return
        else:
            self.request.sendall('802'.encode('utf8'))
            dir_name = os.path.dirname(abs_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            f = open(abs_path, 'wb')
        while has_received < file_size:
            data = self.request.recv(1024)
            f.write(data)
            has_received += len(data)
        f.close()