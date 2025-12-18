SUBDIRS := $(wildcard */Makefile)
SUBDIRS := $(dir $(SUBDIRS))

.PHONY: all help butane clean dryrun fcos-vm clean-vm uninstall $(SUBDIRS)

all: help
help:
	@echo "Available targets:"
	@echo "  butane         - Build Butane specifications suitable for Fedora CoreOS"
	@echo "  clean          - Remove the quadlets persistent data and configuration"
	@echo "  dryrun         - Perform a dry run of the podman systemd generator"
	@echo "  fcos-vm        - Launch a Fedora CoreOS VM with the generated Butane spec"
	@echo "  clean-vm       - Clean up the Fedora CoreOS VM and its resources"
	@echo "  uninstall      - Uninstall the generated resources"

dryrun: $(SUBDIRS)
butane: $(SUBDIRS)
clean: $(SUBDIRS)
fcos-vm: $(SUBDIRS)
clean-vm: $(SUBDIRS)
uninstall: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) -C $@ $(MAKECMDGOALS)
