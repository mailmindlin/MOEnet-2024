default:
	
.PHONY: schema server_stream install

install: /etc/udev/rules.d/80-movidius.rules
	chmod +x ./install.sh
	./install.sh --verbose -y
	make schema

.venv: server/requirements.txt
	python3 -m venv ./.venv
	./.venv/bin/activate
	pip3 install -r --upgrade server/requirements.txt

# We need this for linux
/etc/udev/rules.d/80-movidius.rules:
	echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
	sudo udevadm control --reload-rules
	sudo udevadm trigger

schema: server/config/schema.json
server_stream: ./server/config/schema.json ./server/web/static
	python3 server stream

install_deps:
	pip3 install --upgrade -r server/requirements.txt

./server/web/static:
	pushd ./server/web/static
	npm run build
	popd


./server/config/schema.json: ./server/typedef/cfg.py ./server/typedef/common.py ./server/typedef/geom.py ./server/typedef/apriltag.py
	python3 ./server/typedef/cfg.py --format json LocalConfig > ./server/config/schema.json