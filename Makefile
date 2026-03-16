SHELL := /bin/bash

.PHONY: up demo down clean validate

up:
	./demo.sh up

demo:
	./demo.sh demo

down:
	./demo.sh down

clean:
	./demo.sh clean

validate:
	./demo.sh validate
