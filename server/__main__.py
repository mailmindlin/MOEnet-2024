if __name__ == '__main__':
	from typedef.cfg import LocalConfig
	
	from pathlib import Path
	from argparse import ArgumentParser
	from pydantic_core import ValidationError

	parser = ArgumentParser(
		'server',
		description='MOEnet server'
	)
	parser.add_argument(
		'config',
		type=str,
		nargs='?',
		default='local_nn'
	)
	args = parser.parse_args()
	
	config_name: str = args.config
	if config_name.endswith('.json'):
		config_path = Path(config_name)
	else:
		config_path = Path(__file__).parent.resolve() / f'config/{config_name}.json'
	
	with open(config_path, 'r') as f:
		config_data = f.read()
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
