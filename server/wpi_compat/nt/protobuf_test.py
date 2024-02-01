import time
from ..core_test import NtTestCase
from .protobuf import ProtobufPublisher, ProtobufSubscriber, ProtobufTopic
try:
	from ...typedef.net import Timestamp
except ImportError:
	import sys, os
	sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'typedef'))
	from typedef.net import Timestamp


class NtProtoTest(NtTestCase):
	def test_relay(self):
		default_value = Timestamp(seconds=123, nanos=456)
		with ProtobufTopic.wrap(self.server, "test_proto", Timestamp) as topic:
			with (
				topic.publish() as pub,
				topic.subscribe(default_value) as sub
			):
				ts_int = time.time_ns()
				ts = Timestamp(
					seconds=int(ts_int / 1_000_000_000),
					nanos=int(ts_int % 1_000_000_000),
				)
				# Not published yet
				assert sub.get() == default_value
				assert sub.get("sdf") == "sdf"
				pub.set(ts)
				assert sub.get() == ts