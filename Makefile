SHELL := /bin/bash

.PHONY: up demo demo-re-indicators down clean validate validate-re-indicators

up:
	./demo.sh up

demo:
	./demo.sh demo

demo-re-indicators:
	./demo.sh demo-re-indicators

down:
	./demo.sh down

clean:
	./demo.sh clean

validate:
	./demo.sh validate

validate-re-indicators:
	./demo.sh validate-re-indicators
