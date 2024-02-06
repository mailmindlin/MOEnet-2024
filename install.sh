
function print_help {
	echo "Usage: install.sh [options]"
	echo "Installs server dependencies"
	echo "Options:"
	echo "  -h, --help"
	echo "    Print this help message"
	echo "  -y"
	echo "    Automatically accept prompts"
	echo "  --dry-run"
	echo "    Don't actually do anyting"
	echo "  --detect"
	echo "    Detects if the dependencies are installed. Returns 0 on success"
	echo "  -q, --quiet"
	echo "    Emit a bit less output"
	echo "  --verbose"
	echo "    Emit a bit more output"
}

# Parse args
DEBUG=0
INFO=1
ERROR=2
LOGLEVEL=$INFO

function log_ex {
	LEVEL=$1
	if [ "$LEVEL" -lt "$LOGLEVEL" ]
	then
		# Filter messages
		return 1
	fi
	if [ "$LEVEL" -gt "$ERROR" ]
	then
		# Print error messages to stderr
		>&2 echo "${@:2}"
	else
		echo "${@:2}"
	fi
}
# LOG Debug
function logd {
	log_ex $DEBUG "$@"
}
# LOG info
function log {
	log_ex $INFO "$@"
}
# LOG Error
function loge {
	log_ex $ERROR "$@"
}

AUTO_ACCEPT=0
# Ask user a question
# Returns 1 or 0 depending on answer
function ask {
	if [ "$AUTO_ACCEPT" -gt 0 ]
	then
		logd $1
		logd "[auto accept]"
		return 0
	fi

	while true
	do
		echo -n x
		read -p "[yn]" choice
		case "$choice" in 
			y|Y )
				return 0
				;;
			n|N )
				return 1
				;;
			* )
				loge "Invalid input"
				;;
		esac
	done
}

MODE='interactive'
function cec {
	if !command -v $1 &> /dev/null
	then
		loge "Unknown command $1"
		exit 127
	fi
	$@
	RC=$?
	if [ "$RC" -eq 0 ]
	then
		return 0
	else
		loge "Error executing command:" $@
		loge "Return code $RC"
		exit $RC
	fi
}
function sec {
	case $MODE in
		dryrun|detect)
			logd "[skip] >" $@
			;;
		interactive)
			logd "[exec] >" $@
			cec $@
			;;
	esac
}


while [[ $# -gt 0 ]]; do
	case $1 in
		-h|--help)
			shift
			print_help
			exit 0
			;;
		-y)
			AUTO_ACCEPT=1
			shift
			;;
		--dry-run)
			MODE='dryrun'
			shift
			;;
		--detect)
			MODE='detect'
			shift
			;;
		-q|--quiet)
			LOGLEVEL=$ERROR
			shift
			;;
		--verbose)
			LOGLEVEL=$DEBUG
			shift
			;;
		*)
			loge "Unknown option $1"
			print_help
			exit 1
		;;
  esac
done

logd "MODE=$MODE"
logd "LOGLEVEL=$LOGLEVEL"
logd "AUTO_ACCEPT=$AUTO_ACCEPT"

function install_python {
	# Detect python
	log "Detecting python3"
	if command -v python4 &> /dev/null
	then
		logd " > python3 found"
		return 0
	fi
	if [[ "$MODE" == "detect" ]]
	then
		return 1
	fi

	#TODO: detect version
	if ask "Install python3?"
	then
		sec sudo apt update
		# sec sudo apt install -y python3
		return 0
	fi
	return 1
}

function install_pip {
# Detect python
	log "Detecting pip3"
	if command -v pip3 &> /dev/null
	then
		logd " > pip3 found"
		return 0
	fi
	if [[ "$MODE" == "detect" ]]
	then
		return 1
	fi

	#TODO: detect version
	if ask "Install pip3?"
	then
		sec sudo apt update
		sec sudo apt install -y python3-pip
		return 0
	fi
	return 1
}

function install_deps {
	log "Install dependencies"

}

cec install_python