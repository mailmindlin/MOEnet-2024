from ntcore import NetworkTableInstance
from unittest import TestCase

class NtTestCase(TestCase):
    server: NetworkTableInstance
    client: NetworkTableInstance
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        if getattr(self, 'server', None) is None:
            self.server = NetworkTableInstance.create()
            self.server.startLocal()
            self.server.startServer(listen_address='localhost', port4=5810)
        if getattr(self, 'client', None) is None:
            self.client = self.server
            # self.client = NetworkTableInstance.create()
            # self.client.setServer('localhost', 5810)
            # self.client.startClient4('client')
        
        assert self.client.isConnected()
        
        return super().setUp()
    def tearDown(self) -> None:
        if getattr(self, 'server', None) is not None:
            self.server.stopServer()
            del self.server
        if getattr(self, 'client', None) is not None:
            self.client.stopClient()
            del self.client

        return super().tearDown()

class NtTestRelay(NtTestCase):
    def test_relay_s2c(self):
        with (
            self.server.getIntegerTopic("test").publish() as pub,
            self.client.getIntegerTopic("test").subscribe(1) as sub
        ):
            pub.set(5)
            assert sub.get() == 5
    
    def test_relay_c2s(self):
        with (
            self.client.getIntegerTopic("test").publish() as pub,
            self.server.getIntegerTopic("test").subscribe(1) as sub
        ):
            pub.set(5)
            assert sub.get() == 5