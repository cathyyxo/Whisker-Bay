import asyncio
import secrets
import unittest
from types import SimpleNamespace

import server


class FakePeer:
    def __init__(self, ident):
        self.id = ident
        self.name = None
        self.acc = None
        self.state = None
        self.addr = None
        self.auth_times = []
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def close(self):
        pass


class FakeAccounts:
    def __init__(self):
        self.accounts = {}

    def get(self, name):
        return self.accounts.get(name.lower())

    def create(self, name, password):
        salt = secrets.token_hex(16)
        account = {
            'name': name,
            'salt': salt,
            'iter': server.PBKDF2_ITER,
            'hash': server.hash_pw(password, salt),
            'tokens': [],
            'save': None,
            'rev': 0,
        }
        self.accounts[name.lower()] = account
        return account

    def mark(self, account):
        pass


class ServerSmokeTests(unittest.TestCase):
    def test_two_clients_can_complete_hello_and_registration(self):
        instance = server.Server.__new__(server.Server)
        instance.args = SimpleNamespace(name='Test Bay', motd='Welcome', invite='')
        instance.acc = FakeAccounts()
        instance.clients = {FakePeer('first'), FakePeer('second')}
        instance.by_name = {}
        instance.admins = set()
        instance.creating = set()
        instance.players = lambda: [client for client in instance.clients if client.name]
        instance.broadcast = lambda message, skip=None: [
            client.send(message) for client in instance.players() if client is not skip
        ]
        instance.sys = lambda text, to=None: (
            to.send({'t': 'sys', 'text': text}) if to else
            instance.broadcast({'t': 'sys', 'text': text})
        )
        first, second = sorted(instance.clients, key=lambda client: client.id)

        async def connect_and_register():
            for client in (first, second):
                await instance.on_msg(client, {'t': 'hello', 'v': server.PROTO})
                await instance.on_msg(client, {
                    't': 'register', 'user': f'Angler{client.id.title()}', 'pass': 'testpass123',
                })

        asyncio.run(connect_and_register())

        for client in (first, second):
            messages = [message for message in client.sent if isinstance(message, dict)]
            self.assertTrue(any(message.get('t') == 'welcome' for message in messages))
            self.assertTrue(any(message.get('t') == 'auth_ok' for message in messages))
        self.assertEqual(len(instance.players()), 2)
        self.assertEqual({client.name for client in instance.players()}, {
            'AnglerFirst', 'AnglerSecond',
        })


if __name__ == '__main__':
    unittest.main()
