.PHONY: schema all

all: ./node_modules ./js

./node_modules: package.json
	npm install

js: ./node_modules $(wildcard ts/**/*)
	tsc --build

clean:
	rm -rf ./js
	rm -rf ./node_modules
	rm -rf .tsbuildinfo