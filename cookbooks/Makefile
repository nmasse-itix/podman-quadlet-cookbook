SUBDIRS := $(wildcard */Makefile)
SUBDIRS := $(dir $(SUBDIRS))

.PHONY: all help butane clean dryrun fcos-vm clean-vm uninstall $(SUBDIRS)

export I_KNOW_WHAT_I_AM_DOING ?= no

all: help
help:
	@echo "Available targets:"
	@echo "  butane         - Build Butane specifications suitable for Fedora CoreOS"
	@echo "  clean          - Remove the quadlets persistent data and configuration"
	@echo "  dryrun         - Perform a dry run of the podman systemd generator"
	@echo "  fcos-vm        - Launch a Fedora CoreOS VM with the generated Butane spec"
	@echo "  clean-vm       - Clean up the Fedora CoreOS VM and its resources"
	@echo "  uninstall      - Uninstall the generated resources"
	@echo "  pytest         - Run integration tests on a clean Fedora CoreOS VM"


dryrun: $(SUBDIRS)
butane: $(SUBDIRS)
clean: $(SUBDIRS)
	rm -f local.ign

fcos-vm: $(SUBDIRS)
clean-vm: $(SUBDIRS)
uninstall: $(SUBDIRS)
pytest: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) -C $@ $(MAKECMDGOALS)
