TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

.PHONY: test

test: uninstall clean install
	@echo "Running Nginx tests..."
	curl -sSfL -I http://localhost/
