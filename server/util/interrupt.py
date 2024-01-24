import signal

class InterruptHandler:
	"Context manager to capture SIGINT"
	def __init__(self, callback) -> None:
		self._callback = callback
	def __enter__(self):
		self._prev = signal.signal(signal.SIGINT, self._callback)

	def __exit__(self, *args):
		assert signal.signal(signal.SIGINT, self._prev) is self._callback