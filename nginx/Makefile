PARENT_DIR := ..
include $(PARENT_DIR)/Makefile

.PHONY: test

test: uninstall clean install
	@echo "Running Nginx tests..."
	curl -sSfL -I http://localhost/
