from ..core_test import NtTestCase
from .dynamic import DynamicSubscriber, DynamicPublisher

class DpubTest(NtTestCase):
	def test_start_disabled(self):
		with DynamicPublisher(lambda: self.server.getIntegerTopic("test").publish()) as pub:
			assert not pub.enabled
	
	def test_enable(self):
		with (
			DynamicPublisher(lambda: self.server.getIntegerTopic("test").publish()) as pub,
			self.client.getIntegerTopic("test").subscribe(1) as sub
		):
			pub.set(5)
			assert sub.get() == 1 # Not enabled yet
			pub.enabled = True
			assert sub.get() == 1
			pub.set(5)
			assert sub.get() == 5

class DsubTest(NtTestCase):
	def test_start_disabled(self):
		with DynamicSubscriber(lambda: self.server.getIntegerTopic("test").subscribe(1)) as sub:
			assert not sub.enabled
	
	def test_enable(self):
		with (
			self.server.getIntegerTopic("test").publish() as pub,
			DynamicSubscriber(lambda: self.client.getIntegerTopic("test").subscribe(1)) as sub
		):
			pub.set(5)
			assert sub.get() is None # Not enabled yet
			assert sub.get("sdf") == "sdf" # Not enabled yet
			sub.enabled = True
			assert sub.get() == 5
			assert sub.get("sdf") == 5