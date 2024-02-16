OAKD_RULES = /etc/udev/rules.d/80-movidius.rules
CONFIG_SCHEMA = ./config/schema.json

$(CONFIG_SCHEMA): ./typedef/apriltag.py ./typedef/cfg.py ./typedef/common.py ./typedef/geom.py ./typedef/pipeline.py
	python3 ./server/typedef/cfg.py --format json LocalConfig -o $@

$(OAKD_RULES):
	

.PHONY schema
# Nice alias for schema.json
schema: $(CONFIG_SCHEMA)