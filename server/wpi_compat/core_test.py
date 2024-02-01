from ntcore import NetworkTableInstance
from unittest import TestCase

class NtTestCase(TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.server = None
        self.client = None

    def setUp(self) -> None:
        if self.server is None:
            self.server = NetworkTableInstance.create()
            self.server.startLocal()
            self.server.startServer(listen_address='localhost', port4=5810)
        if self.client is None:
            self.client = self.server
            # self.client = NetworkTableInstance.create()
            # self.client.setServer('localhost', 5810)
            # self.client.startClient4('client')
        
        assert self.client.isConnected()
        
        return super().setUp()
    def tearDown(self) -> None:
        if self.server is not None:
            self.server.stopServer()
            self.server = None
        if self.client is not None:
            self.client.stopClient()
            self.client = None

        return super().tearDown()

class NtTestRelay(NtTestCase):
    def test_relay_s2c(self):
        with (
            self.server.getIntegerTopic("test").publish() as pub,
            self.client.getIntegerTopic("test").subscribe(1) as sub
        ):
            pub.set(5)
            assert sub.get() == 5
    
    def test_relay_s2c(self):
        with (
            self.client.getIntegerTopic("test").publish() as pub,
            self.server.getIntegerTopic("test").subscribe(1) as sub
        ):
            pub.set(5)
            assert sub.get() == 5