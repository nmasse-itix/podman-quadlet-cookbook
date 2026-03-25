# Include common Makefile
include ../../scripts/common.mk

.PHONY: test

test: uninstall clean install
	@echo "Running Nginx tests..."
	curl -sSfL -I http://localhost/
