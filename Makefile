default:
	
.PHONY: schema server_stream install

SERVER_SCHEMA = server/config/schema.json
SERVER_REQUIREMENTS = server/requirements.txt
OAKD_RULES = /etc/udev/rules.d/80-movidius.rules
INSTALL_DEPS =

ifeq ($(OS),Windows_NT)
# Windows
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
		# Linux
		INSTALL_DEPS += $(OAKD_RULES)
    endif
    ifeq ($(UNAME_S),Darwin)
		# MacOS
        CCFLAGS += -D OSX
    endif
endif

install: $(OAKD_RULES)
	chmod +x ./install.sh
	./install.sh --verbose -y
	make schema

.venv: server/requirements.txt
	python3 -m venv ./.venv
	. ./.venv/bin/activate; pip3 install -r --upgrade server/requirements.txt

.venv/server_requirements: server/requirements.txt
	python3 -

# Set up 
# We need this for linux
$(OAKD_RULES):
	echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
	sudo udevadm control --reload-rules
	sudo udevadm trigger

schema: server/config/schema.json

server: schema
	
server_stream: ./server/config/schema.json ./server/web/static
	python3 server stream

install_deps:
	pip3 install --upgrade -r server/requirements.txt

./server/web/static:
	pushd ./server/web/static
	npm run build
	popd


./server/config/schema.json: ./server/typedef/apriltag.py ./server/typedef/cfg.py ./server/typedef/common.py ./server/typedef/geom/__init__.py ./server/typedef/geom/__init__.py
	cd server && $(MAKE) ./config/schema.json

./moenet.service.sh:
	echo "#!/bin/bash" > $@
	echo "python3.11 server" >> $@

./moenet.service: moenet.service.sh
	echo "[Unit]" > $@
	echo "Description=MOEnet service" >> $@
	echo "After=network.target" >> $@
	echo "" >> $@
	echo "[Service]" >> $@
	echo "ExecStart=/bin/bash ./moenet.service.sh" >> $@
	echo "WorkingDirectory=$(shell dirname $(realpath $@))" >> $@
	echo "StandardOutput=inherit" >> $@
	echo "StandardError=inherit" >> $@
	echo "Restart=always" >> $@
	echo "User=$$USER" >> $@
	echo "" >> $@
	echo "[Install]" >> $@
	echo "WantedBy=multi-user.target" >> $@

