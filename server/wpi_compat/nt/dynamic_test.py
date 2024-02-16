from ..core_test import NtTestCase
from .dynamic import DynamicSubscriber, DynamicPublisher
from ntcore import PubSubOptions

class DpubTest(NtTestCase):
	def test_start_disabled(self):
		with DynamicPublisher(lambda: self.server.getIntegerTopic("test").publish()) as pub:
			self.assertFalse(pub.enabled, "Starts disabled")
	
	def test_enable(self):
		with (
			DynamicPublisher(lambda: self.server.getIntegerTopic("test")) as pub,
			self.client.getIntegerTopic("test").subscribe(1) as sub
		):
			pub.set(5)
			self.assertEqual(sub.get(), 1, "Don't publish while disabled")
			pub.enabled = True
			self.assertEqual(sub.get(), 1, "Don't autopublish after enable")
			pub.set(5)
			self.assertEqual(sub.get(), 5, "Publish when enabled")

class DsubTest(NtTestCase):
	def test_start_disabled(self):
		with DynamicSubscriber(lambda: self.server.getIntegerTopic("test"), 1) as sub:
			self.assertFalse(sub.enabled, "Starts disabled")
	
	def test_enable(self):
		with DynamicSubscriber(lambda: self.server.getIntegerTopic("test"), 1, enabled=True) as sub:
			self.assertTrue(sub.enabled)
		
		with (
			self.server.getIntegerTopic("test").publish() as pub,
			DynamicSubscriber(lambda: self.client.getIntegerTopic("test"), 1) as sub
		):
			pub.set(5)
			self.assertIsNone(sub.get(), "Get while disabled")
			self.assertEqual(sub.get("sdf"), "sdf", "Get while disabled returns default")

			sub.enabled = True
			self.assertEqual(sub.get(), 5, "Get enabled returns value")
			self.assertEqual(sub.get("sdf"), 5, "Get enabled returns value")
	
	def test_fresh(self):
		with (
			self.server.getIntegerTopic("test_fresh").publish(PubSubOptions(sendAll=True, keepDuplicates=True)) as pub,
			DynamicSubscriber.create(self.client, "test_fresh", int, 1, PubSubOptions(keepDuplicates=True), enabled=True) as sub
		):
			# No data
			self.assertIsNone(sub.get_fresh(), "No data is not fresh")

			# Get first value
			pub.set(5)
			self.assertEqual(sub.get_fresh(), 5, "Initial value is fresh")
			self.assertIsNone(sub.get_fresh(), "Second call is not fresh")

			# Get new value
			pub.set(6)
			self.assertEqual(sub.get_fresh(), 6, "New value is fresh")
			self.assertIsNone(sub.get_fresh(), "Second call is not fresh")

			# If the same value is published twice, we should still recieve it again
			pub.set(6)
			self.assertEqual(sub.get_fresh(), 6, "Repeated same value is fresh")
			self.assertIsNone(sub.get_fresh(), "Second call is not fresh")
