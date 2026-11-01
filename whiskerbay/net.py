"""A small threaded TCP connection that speaks one JSON message per line."""
import json
import queue
import socket
import threading

MAX_LINE = 1_000_000
_CLOSE = object()


class Conn:
    def __init__(self):
        self.inbox = queue.Queue()
        self.outbox = queue.Queue()
        self.sock = None
        self.alive = False
        self.writer = None

    def connect(self, host, port):
        self.alive = True
        threading.Thread(target=self._run, args=(host, port), daemon=True).start()

    def _run(self, host, port):
        try:
            s = socket.create_connection((host, port), timeout=7)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(None)
            self.sock = s
        except OSError as e:
            self.alive = False
            self.inbox.put({'t': '_fail', 'msg': str(e)})
            return
        if not self.alive:          # cancelled while connecting
            try:
                s.close()
            except OSError:
                pass
            return
        self.inbox.put({'t': '_open'})
        self.writer = threading.Thread(target=self._write, daemon=True)
        self.writer.start()
        f = s.makefile('rb')
        try:
            while self.alive:
                line = f.readline(MAX_LINE)
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict):
                    self.inbox.put(msg)
        except (OSError, ValueError):
            pass
        was_alive = self.alive
        self.alive = False
        self.outbox.put(_CLOSE)
        try:
            s.close()
        except OSError:
            pass
        if was_alive:
            self.inbox.put({'t': '_closed'})

    def _write(self):
        while True:
            item = self.outbox.get()
            if item is _CLOSE or self.sock is None:
                break
            try:
                self.sock.sendall(item)
            except OSError:
                self.alive = False
                break
        if not self.alive:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def send(self, obj):
        if self.alive:
            self.outbox.put((json.dumps(obj, separators=(',', ':')) + '\n').encode('utf-8'))

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self, flush=False, wait=0.0):
        """Hang up. With flush=True, anything already queued is sent first."""
        if flush and self.alive and self.writer:
            self.alive = False
            self.outbox.put(_CLOSE)
            self.writer.join(wait or 1.5)
        self.alive = False
        self.outbox.put(_CLOSE)
        try:
            if self.sock:
                self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass
