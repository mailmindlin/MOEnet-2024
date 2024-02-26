#!/bin/bash

case "$1" in
	install)
		echo "Building service files"
		make server moenet.service
		echo "Adding moenet service to systemctl..."
		sudo cp moenet.service /etc/systemd/system/moenet.service
		sudo systemctl enable moenet.service
		echo "Done."
		;;
	uninstall)
		echo "Removing moenet service from systemctl..."
		sudo systemctl stop moenet.service
		sudo systemctl disable moenet.service
		sudo rm -f /etc/systemd/system/moenet.service
		sudo systemctl daemon-reload
		;;
	start)
		echo "Starting moenet service..."
		sudo systemctl start moenet.service
		;;
	stop)
		echo "Stopping moenet service..."
		sudo systemctl stop moenet.service
		;;
	enable)
		echo "Enabling moenet service to start on boot..."
		sudo systemctl enable moenet.service
		;;
	disable)
		echo "Disabling moenet service from starting on boot..."
		sudo systemctl disable moenet.service
		;;
	help)
		echo ""
		echo "./service_manager.sh argument"
		echo ""
		echo "install - installs moenet service and enables start on boot"
		echo "start - starts moenet via systemctl (service must be installed)"
		echo "stop - stops moenet via systemctl (service must be installed)"
		echo "enable - enables moenet to start on boot (service must be installed)"
		echo "disable - disables moenet from starting on boot (service must be installed)"
		echo "uninstall - completely removes moenet service from systemctl"
		echo ""
		;;
	*)
		echo "Invalid option. Options are help, install, uninstall, enable, disable, start, stop."
		;;
esac