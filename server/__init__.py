
def get_version():
	"Get version info"
	import subprocess, warnings
	try:
		result = subprocess.run(
			['/usr/bin/git', 'log', '-1', '--pretty="format:%h (%ci)"'],
			capture_output=True,
			text=True,
			timeout=1.0,
			check=True,
		)
		return result.stdout
	except FileNotFoundError:
		# Git not installed
		warnings.warn("Git command not installed", RuntimeWarning)
	except subprocess.TimeoutExpired:
		# Git not installed
		warnings.warn("Unable to check version: timed out", RuntimeWarning)
	except subprocess.CalledProcessError as e:
		# Git not installed
		warnings.warn("Git had an error", RuntimeWarning, source=e)
	return "unknown"