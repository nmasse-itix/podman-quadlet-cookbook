SUBDIRS := $(wildcard */Makefile)
SUBDIRS := $(dir $(SUBDIRS))

.PHONY: all help package clean dryrun fcos-vm clean-vm uninstall $(SUBDIRS)

export I_KNOW_WHAT_I_AM_DOING ?= no

all: help
help:
	@echo "Available targets:"
	@echo "  package        - Package the quadlets and systemd units for distribution (Butane, Ignition, tarball, etc.)"
	@echo "  clean          - Remove the quadlets persistent data and configuration"
	@echo "  dryrun         - Perform a dry run of the podman systemd generator"
	@echo "  fcos-vm        - Launch a Fedora CoreOS VM with the generated Butane spec"
	@echo "  clean-vm       - Clean up the Fedora CoreOS VM and its resources"
	@echo "  uninstall      - Uninstall the generated resources"
	@echo "  pytest         - Run integration tests on a clean Fedora CoreOS VM"

dryrun: $(SUBDIRS)
package: $(SUBDIRS)
clean: $(SUBDIRS)

fcos-vm: $(SUBDIRS)
clean-vm: $(SUBDIRS)
uninstall: $(SUBDIRS)
pytest: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) -C $@ $(MAKECMDGOALS)
