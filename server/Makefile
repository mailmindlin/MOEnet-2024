OAKD_RULES = /etc/udev/rules.d/80-movidius.rules
CONFIG_SCHEMA = ./config/schema.json

SCHEMA_DEPS = ./typedef/*

$(CONFIG_SCHEMA): $(SCHEMA_DEPS)
	python3 -m typedef.cfg --format json LocalConfig -o $@

$(OAKD_RULES):
	echo "hi"

.PHONY: schema

# Nice alias for schema.json
schema: $(CONFIG_SCHEMA)
