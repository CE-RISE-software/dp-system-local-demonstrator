SHELL := /bin/bash

.PHONY: up demo demo-re-indicators demo-see-impacts down clean validate validate-re-indicators validate-see-impacts test

up:
	./demo.sh up

demo:
	./demo.sh demo

demo-re-indicators:
	./demo.sh demo-re-indicators

demo-see-impacts:
	./demo.sh demo-see-impacts

down:
	./demo.sh down

clean:
	./demo.sh clean

validate:
	./demo.sh validate

validate-re-indicators:
	./demo.sh validate-re-indicators

validate-see-impacts:
	./demo.sh validate-see-impacts

test:
	python3 -B -m unittest discover -s tests
