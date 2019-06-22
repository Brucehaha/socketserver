import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)


IP = "127.0.0.1"
PORT = 8080
ACCOUNTS_PATH = os.path.join(BASE_DIR, 'conf', 'accounts.cfg')

