#!/usr/bin/bash

default:
	@echo Usage: make [dist|venv]

.PHONY: dist
dist:
	python3 -m build .

.PHONY: venv
venv:
	python3 -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install build
	venv/bin/pip install -e .
