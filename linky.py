
import socket
import threading
import json
import os
import time
import sys

BROADCAST_ADDR = '<broadcast>'

class P2PChat:
    def __init__(self):
        app_dir_name = "ΞΖ"
        if os.name == 'nt':
            self.app_dir = os.path.join(os.getenv('APPDATA'), app_dir_name)
        else:
            self.app_dir = os.path.join(os.path.expanduser('~'), '.config', app_dir_name)
        os.makedirs(self.app_dir, exist_ok=True)

        self.config_file = os.path.join(self.app_dir, 'config.json')
        self.config = self.load_config()
        self.username = self.config.get('username')
        self.port = self.config.get('port')
        self.history_file = None
        self.peers = {}
        self.screen_lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_config(self, key, value):
        config = self.load_config()
        config[key] = value
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        self.config = config

    def display_splash_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        blue = '\033[94m'
        bold_red = '\033[1;91m'
        reset = '\033[0m'

        art = [
            "ooooo        ooooo ooooo      ooo oooo    oooo oooooo   oooo",
            "`888'        `888' `888b.     `8' `888   .8P'   `888.   .8' ",
            " 888          888   8 `88b.    8   888  d8'      `888. .8'  ",
            " 888          888   8   `88b.  8   88888[         `888.8'   ",
            " 888          888   8     `88b.8   888`88b.        `888'    ",
            " 888       o  888   8       `888   888  `88b.       888     ",
            "o888ooooood8 o888o o8o        `8  o888o  o888o     o888o    "
]

        splash_art = blue + "\n".join(art) + reset
        splash_art += f"\n\n{bold_red}                         Made by ΞΖ{reset}\n"

        sys.stdout.buffer.write(splash_art.encode('utf-8'))
        time.sleep(2)

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                message = json.loads(data.decode())
                self.handle_message(message, addr)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

    def handle_message(self, message, addr):
        msg_type = message.get('type')
        sender_name = message.get('username', 'unknown')

        if addr[0] == self.get_my_ip() or sender_name == self.username:
            return

        with self.screen_lock:
            sys.stdout.write('\r' + ' ' * 80 + '\r')

            if msg_type == 'hello':
                if sender_name not in self.peers:
                    print(f'[System: {sender_name} joined the chat.]')
                self.peers[sender_name] = addr[0]
            elif msg_type == 'group':
                chat_message = f'<{sender_name}> {message["text"]}'
                print(chat_message)
                self.log_message(chat_message)
            elif msg_type == 'namechange':
                old_name = message.get('old')
                new_name = message.get('new')
                if old_name in self.peers:
                    self.peers[new_name] = self.peers.pop(old_name)
                    print(f'[System: {old_name} is now known as {new_name}]')
            
            sys.stdout.write(f'<{self.username}> ')
            sys.stdout.flush()

    def send_broadcast(self, message):
        message['username'] = self.username
        self.sock.sendto(json.dumps(message).encode(), (BROADCAST_ADDR, self.port))

    def start(self):
        self.display_splash_screen()
        if not self.username:
            self.prompt_for_username()

        if not self.port:
            self.prompt_for_port()

        self.sock.bind(('', self.port))
        
        print(f"Welcome, {self.username}!")
        print(f"Connecting to the network on port {self.port}...")
        self.history_file = os.path.join(self.app_dir, f"{self.port}.log")
        time.sleep(1)

        print("Commands: @myname <name>, @people, @quit")

        listener_thread = threading.Thread(target=self.listen, daemon=True)
        listener_thread.start()

        def announcer():
            while True:
                self.send_broadcast({'type': 'hello'})
                time.sleep(10)

        announcer_thread = threading.Thread(target=announcer, daemon=True)
        announcer_thread.start()

        self.main_loop()

    def prompt_for_username(self):
        while not self.username:
            new_name = input("Please enter your name to begin: ").strip()
            if new_name:
                self.username = new_name
                self.save_config('username', new_name)
            else:
                print("Name cannot be empty.")

    def prompt_for_port(self):
        while not self.port:
            try:
                port_str = input("Please enter a port to use (1024-65535): ").strip()
                port = int(port_str)
                if 1024 <= port <= 65535:
                    self.port = port
                    self.save_config('port', self.port)
                    break
                else:
                    print("Port must be between 1024 and 65535.")
            except ValueError:
                print("Invalid port number.")

    def main_loop(self):
        self.load_history()

        while True:
            try:
                with self.screen_lock:
                    sys.stdout.write(f'<{self.username}> ')
                    sys.stdout.flush()
                
                msg = sys.stdin.readline().strip()
                if not msg:
                    continue

                if msg.startswith('@'):
                    parts = msg.split(' ')
                    command = parts[0]
                    if command in ('@myname', '@m'):
                        new_name = ' '.join(parts[1:])
                        if new_name:
                            old_name = self.username
                            self.username = new_name
                            self.save_config('username', new_name)
                            print(f'[System: Your name is now {self.username}]')
                            self.send_broadcast({'type': 'namechange', 'old': old_name, 'new': new_name})
                        else:
                            print('[System: Usage: @myname <your_name>]')
                    elif command in ('@people', '@p'):
                        with self.screen_lock:
                            print('[Online Users:]')
                            if not self.peers:
                                print('  (No one else is here right now)')
                            else:
                                for name in self.peers:
                                    print(f'  - {name}')
                    elif command in ('@quit', '@q'):
                        print('[System: Quitting...]')
                        break
                    else:
                        print(f'[System: Unknown command "{command}"]')
                else:
                    self.send_broadcast({'type': 'group', 'text': msg})
                    self.log_message(f'<{self.username}> {msg}')
            except (KeyboardInterrupt, EOFError):
                print('\n[System: Quitting...]')
                break

    def log_message(self, text):
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(text + '\n')

    def load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    print(line.strip())

    def get_my_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

if __name__ == '__main__':
    chat = P2PChat()
    chat.start()
