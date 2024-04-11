def check_python_version():
	import sys
	if (sys.version_info < (3, 12)):
		raise RuntimeError("Minimum required python: 3.12")

def parse_args(config_dir: 'Path'):
	from argparse import ArgumentParser

	parser = ArgumentParser(
		'server',
		description='MOEnet server'
	)

	class ConfigChoices:
		"Helper collection for the 'config' argument"
		def __iter__(self):
			for path in config_dir.glob('*.json'):
				yield str(path.relative_to(config_dir)).removesuffix('.json')
		def __contains__(self, choice: str):
			if choice.endswith('.json'):
				return True
			child_path = config_dir / f'{choice}.json'
			return child_path.exists()

	parser.add_argument(
		'config',
		type=str,
		default='local_nn',
		help="Configuration name",
		choices=ConfigChoices(),
		metavar='choices',
	)
	return parser.parse_args()

if __name__ == '__main__':
	check_python_version()

	# Config directory (TODO: allow ENV override?)
	from pathlib import Path
	config_dir = Path(__file__).parent.resolve() / 'config'
	args = parse_args(config_dir)
	
	config_name: str = args.config
	if config_name.endswith('.json'):
		config_path = Path(config_name)
	else:
		config_path = config_dir / f'{config_name}.json'
	
	# Read config file
	with open(config_path, 'r') as f:
		config_data = f.read()
	
	# Parse config file
	from typedef.cfg import LocalConfig
	from pydantic_core import ValidationError
	try:
		local_cfg = LocalConfig.model_validate_json(config_data)
		del config_data
	except ValidationError:
		print("ERROR: Local config validation failure")
		raise

	from moenet import MoeNet
	moenet = MoeNet(config_path, local_cfg)
	try:
		moenet.run()
	finally:
		moenet.cleanup()
