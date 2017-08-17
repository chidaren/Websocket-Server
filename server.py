import socket
import threading
import hashlib
import base64
import logging

logging.basicConfig(level=logging.INFO)

ws = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

handshake_header = 'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n' \
       'Sec-WebSocket-Accept: {}\r\n\r\n'


def get_sec_key_from_raw_header(data, sep):
    index = data.find("Sec-WebSocket-Key")
    if index == -1:
        return None
    end = data.find(sep, index)
    return str.strip(data[index + len("Sec-WebSocket-Key:"):end])


class Buffer(object):

    def __init__(self, sock):
        self.data = ''
        self.sock = sock
        sock.setblocking(0)

    def read_one_byte(self):
        while True:
            if len(self.data) == 0:
                try:
                    self.data += self.sock.recv(1)
                except:
                    pass
                if len(self.data) == 0:
                    continue
            byte = self.data[0]
            self.data = self.data[1:]
            return ord(byte)

    def read_bytes(self, amont):
        while True:
            if len(self.data) < amont:
                try:
                    self.data += self.sock.recv(2048)
                except:
                    pass
                if len(self.data) < amont:
                    continue
            bytes = self.data[:amont]
            self.data = self.data[amont:]
            return bytes

    def peek_read_full(self):
        try:
            self.data += self.sock.recv(2048)
        except:
            pass
        bytes = self.data
        return bytes

    def discard(self, amount):
        self.data = self.data[amount:]

    def send(self, data):
        self.sock.send(data)


class WebSocket(object):

    def __init__(self, buffer, addr, msg):
        self.buffer = buffer
        self.addr = addr
        self.msgs = msg
        sep = "\n"
        bytes = ''
        while True:
            bytes += buffer.peek_read_full()
            if bytes[-2:] == "\n\n" or bytes[-4:] == "\r\n\r\n":
                if bytes[-4:] == "\r\n\r\n":
                    sep = "\r\n"
                header_length = bytes.index(sep + sep) + len(sep + sep)
                buffer.discard(header_length)
                sec_key = get_sec_key_from_raw_header(bytes, sep)
                crypted_key = base64.b64encode(hashlib.sha1(sec_key + ws).digest())
                buffer.send(handshake_header.format(crypted_key))
                self._handler()
                break

    def _send(self, msg):
        fin = 1
        opcode = 1
        mask = 0
        payload_len = len(msg)
        first_byte = fin << 7
        two_byte = first_byte

    def _handler(self):
        sock = self.buffer
        while True:
            first_byte = sock.read_one_byte()
            fin = first_byte >> 7
            opcode = first_byte & 0xf
            if opcode == 8:
                self.msgs.append(str(addr) + '...: ' + 'offline')
                break
            if opcode == 9:
                self.msgs.append(str(addr) + '...: ' + 'say hi')
            two_byte = sock.read_one_byte()
            mask = two_byte >> 7
            length = payload_len = two_byte & 0x7f
            if payload_len == 126:
                length = (sock.read_one_byte() << 8) + sock.read_one_byte()
            if payload_len == 127:
                sock.read_bytes(4)
                length = (sock.read_one_byte() << 24) + (sock.read_one_byte() << 16) \
                         + (sock.read_one_byte() << 8) + sock.read_one_byte()
            if mask:
                mask_key = sock.read_bytes(4)
                msg = ''
                for i in range(length):
                    msg += chr(sock.read_one_byte() ^ ord(mask_key[i % 4]))
            else:
                msg = sock.read_bytes(length)
            msg = str(addr) + '...: ' + msg
            self.msgs.append(msg)


def SocketHandler(sock, addr, msg):
    WebSocket(sock, addr,  msg)


def msg_handler(msg=[]):
    while True:
        if len(msg) > 0:
            print msg[0]
            msg.pop(0)


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 8888))
    s.listen(10)
    msg = ["Server Start..."]
    threading.Thread(target=msg_handler, kwargs=dict(msg=msg)).start()

    while True:
        sock, addr = s.accept()
        t = threading.Thread(target=SocketHandler, args=(Buffer(sock), addr, msg))
        t.start()
