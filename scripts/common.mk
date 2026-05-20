all: help
help:
	@echo
	@echo "================================================"
	@echo " Project '$(PROJECT_NAME)'"
	@echo "================================================"
	@echo
	@echo "Relevant paths and settings:"
	@echo
	@echo "  Configuration directory:         /etc/quadlets/$(PROJECT_NAME)"
	@echo "  Persistent Storage directory:    /var/lib/quadlets/$(PROJECT_NAME)"
	@echo "  UID & GID for project files:     $(PROJECT_UID):$(PROJECT_GID)"
	@echo "  Dependencies:                    $(if $(DEPENDENCIES),$(DEPENDENCIES),none)"
	@echo
	@echo "Available targets:"
	@echo
	@echo "  help           - Show this help message"
	@echo "  install        - Install quadlets and systemd units"
	@echo "  uninstall      - Uninstall quadlets and systemd units"
	@echo "  clean          - Remove the quadlets persistent data and configuration"
	@echo "  dryrun         - Perform a dry run of the podman systemd generator"
	@echo "  tail-logs      - Tail the logs of the quadlet units"
	@echo "  package        - Package the quadlets and systemd units for distribution (Butane, Ignition, tarball, etc.)"
	@echo "  fcos-vm        - Launch a Fedora CoreOS VM with the generated Butane spec"
	@echo "  clean-vm       - Clean up the Fedora CoreOS VM but keep its storage resources"
	@echo "  remove-vm      - Remove all resources related to the Fedora CoreOS VM"
	@echo "  console        - Connect to the Fedora CoreOS VM console"
	@echo "  pytest         - Run integration tests on a clean Fedora CoreOS VM"
	@echo "  debug 		    - Dump makefile variables for debugging purposes"
	@echo
	@echo "Useful commands:"
	@echo
	@echo "  1. make uninstall install                    # Replace quadlets and systemd units"
	@echo "  2. make uninstall clean install              # Same but also remove persistent data and configuration"
	@echo "  3. make uninstall install tail-logs          # Replace quadlets and systemd units, then tail their logs"
	@echo "  4. make I_KNOW_WHAT_I_AM_DOING=yes clean     # Remove all persistent data and configuration without confirmation"
	@echo "  5. make package                              # Package the quadlets and systemd units for distribution (Butane, Ignition, tarball, etc.)"
	@echo "  6. make fcos-vm console                      # Launch a fresh Fedora CoreOS VM (while retaining its persistent data) and connect to its console"
	@echo "  7. make remove-vm                            # Remove all resources related to the Fedora CoreOS VM"
	@echo "  8. make pytest                               # Run integration tests on a clean Fedora CoreOS VM"
	@echo "  9. make debug | sort   				      # Dump makefile variables for debugging purposes"
	@echo
	@echo "All-in-one commands:"
	@echo
	@echo "  1. make I_KNOW_WHAT_I_AM_DOING=yes uninstall clean install tail-logs"
	@echo "  2. make fcos-vm console"
	@echo

# Absolute paths derived from the location of this Makefile
SCRIPTS_DIR := $(shell realpath $(dir $(lastword $(MAKEFILE_LIST))))
TOP_LEVEL_DIR := $(shell realpath $(SCRIPTS_DIR)/..)
COOKBOOKS_DIR := $(shell realpath $(TOP_LEVEL_DIR)/cookbooks)

# Create a temporary directory as target chroot when we detect that we are building Butane specs or launching a Fedora CoreOS VM.
ifneq ($(filter %.ign %.bu package fcos-vm,$(MAKECMDGOALS)),)
ifeq ($(TARGET_CHROOT),)
export TARGET_CHROOT := $(shell mktemp -d /tmp/butane-chroot-XXXXXX)
endif
ifeq ($(BUTANE_BLOCKLIST),)
export BUTANE_BLOCKLIST := $(shell tmp=$$(mktemp /tmp/butane-blocklist-XXXXXX); cp $(SCRIPTS_DIR)/butane.blocklist "$$tmp"; echo "$$tmp")
endif
ifeq ($(BUTANE_START_TS),)
export BUTANE_START_TS := $(shell mktemp /tmp/butane-start-ts-XXXXXX)
endif
endif

# Name of the current project, derived from the current working directory.
# This is used to create subdirectories for configuration and state files.
PROJECT_NAME := $(shell basename "$${PWD}")

# Quadlets files and their corresponding systemd unit names
QUADLETS_FILES = $(wildcard *.container *.volume *.network *.pod *.build *.image)
QUADLET_UNIT_NAMES := $(patsubst %.container, %.service, $(wildcard *.container)) \
					 $(patsubst %.volume, %-volume.service, $(wildcard *.volume)) \
					 $(patsubst %.network, %-network.service, $(wildcard *.network)) \
					 $(patsubst %.pod, %-pod.service, $(wildcard *.pod)) \
					 $(patsubst %.build, %-build.service, $(wildcard *.build)) \
					 $(patsubst %.image, %-image.service, $(wildcard *.image))

# Wellknown systemd unit file types
SYSTEMD_FILES = $(wildcard *.service *.target *.timer *.mount)
SYSTEMD_UNIT_NAMES := $(wildcard *.service *.target *.timer *.mount)
SYSTEMD_TIMER_NAMES := $(wildcard *.timer)

# The main systemd units will be enabled and started after installation.
SYSTEMD_MAIN_UNIT_NAMES := $(wildcard *.target)

# Configuration files
CONFIG_FILES := $(shell find config/ -mindepth 1 \! -path "config/examples/*" \! -path "config/examples" 2>/dev/null)
TMPFILESD_FILES = $(filter-out %/examples, $(wildcard tmpfiles.d/*))
SYSCTLD_FILES = $(filter-out %/examples, $(wildcard sysctl.d/*))
PROFILED_FILES = $(filter-out %/examples, $(wildcard profile.d/*))
TARGET_CONFIG_FILES = $(patsubst config/%, $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)/%, $(CONFIG_FILES))
TARGET_TMPFILESD_FILES = $(patsubst tmpfiles.d/%, $(TARGET_CHROOT)/etc/tmpfiles.d/%, $(TMPFILESD_FILES))
TARGET_SYSCTLD_FILES = $(patsubst sysctl.d/%, $(TARGET_CHROOT)/etc/sysctl.d/%, $(SYSCTLD_FILES))
TARGET_PROFILED_FILES = $(patsubst profile.d/%, $(TARGET_CHROOT)/etc/profile.d/%, $(PROFILED_FILES))

# Example configuration files
EXAMPLES_CONFIG_FILES := $(shell find config/examples -mindepth 1 2>/dev/null)
EXAMPLES_TMPFILESD_FILES = $(wildcard tmpfiles.d/examples/*)
EXAMPLES_SYSCTLD_FILES = $(wildcard sysctl.d/examples/*)
EXAMPLES_PROFILED_FILES = $(wildcard profile.d/examples/*)
TARGET_EXAMPLES_CONFIG_FILES = $(patsubst config/examples/%, $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)/%, $(EXAMPLES_CONFIG_FILES))
TARGET_EXAMPLES_TMPFILESD_FILES = $(patsubst tmpfiles.d/examples/%, $(TARGET_CHROOT)/etc/tmpfiles.d/%, $(EXAMPLES_TMPFILESD_FILES))
TARGET_EXAMPLES_SYSCTLD_FILES = $(patsubst sysctl.d/examples/%, $(TARGET_CHROOT)/etc/sysctl.d/%, $(EXAMPLES_SYSCTLD_FILES))
TARGET_EXAMPLES_PROFILED_FILES = $(patsubst profile.d/examples/%, $(TARGET_CHROOT)/etc/profile.d/%, $(EXAMPLES_PROFILED_FILES))

# Example quadlet and systemd drop-ins files
EXAMPLES_QUADLET_DROPINS_FILES := $(shell if [ -d examples ]; then find examples -mindepth 1 -type f | grep -E '\.(container|volume|network|pod|build|image)\.d/' 2>/dev/null; fi)
EXAMPLES_SYSTEMD_DROPINS_FILES := $(shell if [ -d examples ]; then find examples -mindepth 1 -type f | grep -E '\.(service|target|timer|mount)\.d/' 2>/dev/null; fi)
TARGET_EXAMPLES_QUADLET_DROPINS_FILES = $(patsubst examples/%, $(TARGET_CHROOT)/etc/containers/systemd/%, $(EXAMPLES_QUADLET_DROPINS_FILES))
TARGET_EXAMPLES_SYSTEMD_DROPINS_FILES = $(patsubst examples/%, $(TARGET_CHROOT)/etc/systemd/system/%, $(EXAMPLES_SYSTEMD_DROPINS_FILES))

# All configuration files to be installed
TARGET_FILES += $(addprefix $(TARGET_CHROOT)/etc/containers/systemd/, $(QUADLETS_FILES)) \
				$(addprefix $(TARGET_CHROOT)/etc/systemd/system/, $(SYSTEMD_FILES)) \
				$(TARGET_CONFIG_FILES) $(TARGET_TMPFILESD_FILES) $(TARGET_SYSCTLD_FILES) $(TARGET_PROFILED_FILES)

# All example configuration files to be installed
TARGET_EXAMPLE_FILES += $(TARGET_EXAMPLES_CONFIG_FILES) $(TARGET_EXAMPLES_TMPFILESD_FILES) $(TARGET_EXAMPLES_SYSCTLD_FILES) $(TARGET_EXAMPLES_PROFILED_FILES) $(TARGET_EXAMPLES_QUADLET_DROPINS_FILES) $(TARGET_EXAMPLES_SYSTEMD_DROPINS_FILES)

# Dependencies on other projects
# List here the names of other projects (directories at the top-level) that this project depends on.
DEPENDENCIES ?= 

# Set this variable to "yes" to skip the confirmation prompt when running "make clean".
I_KNOW_WHAT_I_AM_DOING ?= 

# List of all ignition files corresponding to the dependencies
# Here, we inject the "base" project as a dependency. It can therefore be assumed to always be embeddable in project's butane specs.
DEPENDENCIES_IGNITION_FILES := $(shell for dep in $$(if [ "$(PROJECT_NAME)" != "base" ]; then echo base; fi) $(DEPENDENCIES); do echo $(COOKBOOKS_DIR)/$$dep/build/$$dep.ign; done)

# Variation of the previous variable with the built-in examples.
DEPENDENCIES_IGNITION_EXAMPLES_FILES := $(shell for dep in $$(if [ "$(PROJECT_NAME)" != "base" ]; then echo base; fi) $(DEPENDENCIES); do echo $(COOKBOOKS_DIR)/$$dep/build/$$dep.ign $(COOKBOOKS_DIR)/$$dep/build/$$dep-examples.ign; done)

# User and group IDs to own the project files and directories.
PROJECT_UID ?= 0
PROJECT_GID ?= 0

# Source Makefiles providing hooks to extend this Makefile.
HOOKS := $(wildcard $(COOKBOOKS_DIR)/*/hooks.mk)
include $(HOOKS)

# Dump makefile variables for debugging purposes
debug:
	$(foreach v, $(filter %_FILES SYSTEMD_% QUADLET% PROJECT_% DEPENDENCIES% %_DIR, $(.VARIABLES)), $(info $(v): $($(v))))
	@echo "TARGET_CHROOT: $(TARGET_CHROOT)"
	@echo "BUTANE_BLOCKLIST: $(BUTANE_BLOCKLIST)"
	@echo "BUTANE_START_TS: $(BUTANE_START_TS)"
	@echo "HOOKS: $(HOOKS)"
	@echo "I_KNOW_WHAT_I_AM_DOING: $(I_KNOW_WHAT_I_AM_DOING)"

# Ensure that the Makefile is run as root.
pre-requisites::
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "This Makefile must be run as root" >&2; \
		exit 1; \
	fi
	@set -Eeuo pipefail; \
	for tool in install systemctl systemd-analyze systemd-tmpfiles sysctl virt-install virsh qemu-img journalctl coreos-installer resize butane yq podlet pip3 ncat; do \
		if ! which $$tool &>/dev/null ; then \
			echo "$$tool is not installed. Please install it first." >&2; \
			exit 1; \
		fi ; \
	done

# Perform a dry run of the podman systemd generator to validate the quadlet and systemd files.
dryrun:
	QUADLET_UNIT_DIRS="$$PWD" /usr/lib/systemd/system-generators/podman-system-generator -dryrun > /dev/null

# Create the base directories needed for installation.
$(TARGET_CHROOT)/etc/containers/systemd $(TARGET_CHROOT)/etc/systemd/system $(TARGET_CHROOT)/etc/tmpfiles.d $(TARGET_CHROOT)/etc/sysctl.d $(TARGET_CHROOT)/etc/profile.d:
	install -D -d -m 0755 -o root -g root $@

# Create the directory to store quadlet configuration files.
$(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME):
	install -D -d -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) $@

# Copy quadlet files
$(TARGET_CHROOT)/etc/containers/systemd/%: % $(TARGET_CHROOT)/etc/containers/systemd
	install -m 0644 -o root -g root $< $@

# Copy systemd unit files
$(TARGET_CHROOT)/etc/systemd/system/%: % $(TARGET_CHROOT)/etc/systemd/system
	install -m 0644 -o root -g root $< $@

# Copy configuration files, handling executable and non-executable files differently.
$(TARGET_CONFIG_FILES): $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)/%: config/% $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)
$(TARGET_EXAMPLES_CONFIG_FILES): $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)/%: config/examples/% $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)
$(filter-out %.env, $(TARGET_CONFIG_FILES) $(TARGET_EXAMPLES_CONFIG_FILES)):
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	if [ -d $< ]; then \
		run install -d -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) $@; \
	else \
		if [ -x $< ]; then \
			run install -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@; \
		else \
			run install -m 0644 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@; \
		fi ; \
	fi; \

# Handle .env files separately to set more restrictive permissions
$(filter %.env, $(TARGET_CONFIG_FILES) $(TARGET_EXAMPLES_CONFIG_FILES)):
	install -m 0600 -o root -g root -D $< $@

# Copy systemd and quadlet drop-ins files
$(TARGET_EXAMPLES_QUADLET_DROPINS_FILES): $(TARGET_CHROOT)/etc/containers/systemd/%: examples/% $(TARGET_CHROOT)/etc/containers/systemd
$(TARGET_EXAMPLES_SYSTEMD_DROPINS_FILES): $(TARGET_CHROOT)/etc/systemd/system/%: examples/% $(TARGET_CHROOT)/etc/systemd/system
$(TARGET_EXAMPLES_QUADLET_DROPINS_FILES) $(TARGET_EXAMPLES_SYSTEMD_DROPINS_FILES):
	install -D -m 0644 -o root -g root $< $@

# Copy tmpfiles.d files
$(TARGET_TMPFILESD_FILES): $(TARGET_CHROOT)/etc/tmpfiles.d/%: tmpfiles.d/% $(TARGET_CHROOT)/etc/tmpfiles.d
$(TARGET_EXAMPLES_TMPFILESD_FILES): $(TARGET_CHROOT)/etc/tmpfiles.d/%: tmpfiles.d/examples/% $(TARGET_CHROOT)/etc/tmpfiles.d
$(TARGET_TMPFILESD_FILES) $(TARGET_EXAMPLES_TMPFILESD_FILES):
	install -D -m 0644 -o root -g root $< $@

# Copy sysctl.d files
$(TARGET_SYSCTLD_FILES): $(TARGET_CHROOT)/etc/sysctl.d/%: sysctl.d/% $(TARGET_CHROOT)/etc/sysctl.d
$(TARGET_EXAMPLES_SYSCTLD_FILES): $(TARGET_CHROOT)/etc/sysctl.d/%: sysctl.d/examples/% $(TARGET_CHROOT)/etc/sysctl.d
$(TARGET_SYSCTLD_FILES) $(TARGET_EXAMPLES_SYSCTLD_FILES):
	install -D -m 0644 -o root -g root $< $@

# Copy profile.d files
$(TARGET_PROFILED_FILES): $(TARGET_CHROOT)/etc/profile.d/%: profile.d/% $(TARGET_CHROOT)/etc/profile.d
$(TARGET_EXAMPLES_PROFILED_FILES): $(TARGET_CHROOT)/etc/profile.d/%: profile.d/examples/% $(TARGET_CHROOT)/etc/profile.d
$(TARGET_PROFILED_FILES) $(TARGET_EXAMPLES_PROFILED_FILES):
	install -D -m 0644 -o root -g root $< $@

# Create the directory to store quadlet state and data.
$(TARGET_CHROOT)/var/lib/quadlets/$(PROJECT_NAME):
	install -d -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) $@

# Copy all configuration files provided by this project.
install-config: $(TARGET_FILES) $(TARGET_CHROOT)/var/lib/quadlets/$(PROJECT_NAME) $(TARGET_CHROOT)/etc/quadlets/$(PROJECT_NAME)

# Copy all example configuration files provided by this project.
install-examples: $(TARGET_EXAMPLE_FILES)

# Copy all quadlets and systemd files provided by this project.
install-files: install-files-pre install-config install-examples
	$(MAKE) install-files-post

# Custom commands to be run before copying quadlets and systemd files.
# This target can be extended by Makefiles sourcing this one.
install-files-pre::
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	for dep in $(DEPENDENCIES); do \
		run $(MAKE) -C $(COOKBOOKS_DIR)/$$dep install-files; \
	done

# Custom commands to be run after copying quadlets and systemd files.
# This target can be extended by Makefiles sourcing this one.
install-files-post::

# Generated systemd units (quadlets) cannot be enabled.
# That's why we filter them out from the list of units to be enabled.
install-actions uninstall: ENABLE_UNITS = $(filter-out $(QUADLET_UNIT_NAMES),$(SYSTEMD_MAIN_UNIT_NAMES) $(SYSTEMD_TIMER_NAMES))
install-actions uninstall: START_UNITS = $(SYSTEMD_MAIN_UNIT_NAMES)

# Perform post-installation actions such as enabling and starting units.
install-actions: install-actions-pre
	systemctl daemon-reload
	systemd-analyze --generators=true verify $(QUADLET_UNIT_NAMES) $(SYSTEMD_UNIT_NAMES)
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	if [ -f /etc/tmpfiles.d/$(PROJECT_NAME).conf ]; then \
		run systemd-tmpfiles --create /etc/tmpfiles.d/$(PROJECT_NAME).conf; \
	fi; \
	if [ -f /etc/sysctl.d/$(PROJECT_NAME).conf ]; then \
		run sysctl -q -p /etc/sysctl.d/$(PROJECT_NAME).conf; \
	fi ; \
	if [ -n "$(ENABLE_UNITS)" ]; then \
		run systemctl enable $(ENABLE_UNITS); \
	fi ; \
	if [ -n "$(START_UNITS)" ]; then \
		run systemctl start $(START_UNITS); \
	fi
	$(MAKE) install-actions-post

# Custom commands to be run before performing post-installation actions.
# This target can be extended by Makefiles sourcing this one.
install-actions-pre::
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	for dep in $(DEPENDENCIES); do \
		run $(MAKE) -C $(COOKBOOKS_DIR)/$$dep install-actions; \
	done

# Custom commands to be run after performing post-installation actions.
# This target can be extended by Makefiles sourcing this one.
install-actions-post::

# Install all quadlets and systemd units provided by this project.
install: pre-requisites dryrun install-pre
	$(MAKE) install-files
	$(MAKE) install-actions
	$(MAKE) install-post

# Custom commands to be run before installing quadlets and systemd units.
# This target can be extended by Makefiles sourcing this one.
install-pre::

# Custom commands to be run after installing quadlets and systemd units.
# This target can be extended by Makefiles sourcing this one.
install-post::

# All files to be removed during uninstallation, sorted in reverse order to remove files before their parent directories.
uninstall: FILES_TO_REMOVE := $(shell echo $(TARGET_FILES) $(TARGET_EXAMPLE_FILES) | tr ' ' '\n' | sort -ur | tr '\n' ' ')

# Uninstall all quadlets and systemd units installed by this project.
uninstall: pre-requisites uninstall-pre
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	if [ -n "$(ENABLE_UNITS)" ]; then \
		run systemctl disable $(ENABLE_UNITS) || true; \
	fi ; \
	if [ -n "$(START_UNITS)" ]; then \
		run systemctl stop $(START_UNITS) || true; \
	fi
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	if [ -f /etc/tmpfiles.d/$(PROJECT_NAME).conf ]; then \
		run systemd-tmpfiles --purge /etc/tmpfiles.d/$(PROJECT_NAME).conf; \
	fi
	rm -df $(FILES_TO_REMOVE)
	systemctl daemon-reload
	$(MAKE) uninstall-post

# Custom commands to be run before uninstalling quadlets and systemd units.
# This target can be extended by Makefiles sourcing this one.
uninstall-pre::

# Custom commands to be run after uninstalling quadlets and systemd units.
# This target can be extended by Makefiles sourcing this one.
uninstall-post::
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
    for dep in $(DEPENDENCIES); do \
		run $(MAKE) -C $(COOKBOOKS_DIR)/$$dep uninstall; \
	done

# Tail the logs of all units managed by this project.
tail-logs: pre-requisites
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	declare -a journalctl_args=( -f ); \
	for unit in $$($(MAKE) -s units 2>/dev/null | sort -u); do \
		journalctl_args+=( -u "$$unit" ); \
	done; \
	run journalctl "$${journalctl_args[@]}"

pytest: pre-requisites
	$(MAKE) package
	pytest tests/

# Build the Butane specifications, suitable for Fedora CoreOS, including those of the dependencies of this project.
build/$(PROJECT_NAME).tar.gz build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu: export PROJECT_NAME := $(PROJECT_NAME)
build/$(PROJECT_NAME).tar.gz build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu: export TARGET_CHROOT := $(TARGET_CHROOT)
build/$(PROJECT_NAME).tar.gz build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu: export BUTANE_BLOCKLIST := $(BUTANE_BLOCKLIST)
build/$(PROJECT_NAME).tar.gz build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu: export SYSTEMD_MAIN_UNIT_NAMES := $(SYSTEMD_MAIN_UNIT_NAMES)
build/$(PROJECT_NAME).tar.gz build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu: export SYSTEMD_TIMER_NAMES := $(SYSTEMD_TIMER_NAMES)
build/$(PROJECT_NAME).tar.gz build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu &: 
	@if [ -z "$(TARGET_CHROOT)" ]; then \
		echo "TARGET_CHROOT is not set!"; exit 1; \
	fi; \
	if [ -z "$(BUTANE_BLOCKLIST)" ]; then \
		echo "BUTANE_BLOCKLIST is not set!"; exit 1; \
	fi; \
	if [ -z "$(BUTANE_START_TS)" ]; then \
		echo "BUTANE_START_TS is not set!"; exit 1; \
	fi
	@run() { echo $$*; "$$@"; }; \
	run mkdir -p build; \
	export ALL_DEPS="$(shell $(MAKE) -s list-dependencies 2>/dev/null)"; \
	set -Eeuo pipefail; \
	if [ build/$(PROJECT_NAME).bu -ot "$(BUTANE_START_TS)" ] || [ build/$(PROJECT_NAME)-examples.bu -ot "$(BUTANE_START_TS)" ]; then \
		for dep in base $(DEPENDENCIES); do \
			if [[ "$$dep" == "$(PROJECT_NAME)" ]]; then \
				# Avoid building the current project as its own dependency. \
				continue; \
			fi ; \
			if [ $(BUTANE_START_TS) -ot "$(COOKBOOKS_DIR)/$$dep/build/$$dep.ign" ] && [ $(BUTANE_START_TS) -ot "$(COOKBOOKS_DIR)/$$dep/build/$$dep-examples.ign" ]; then \
				# Dependency is up-to-date. \
				continue; \
			fi ; \
			run $(MAKE) -C $(COOKBOOKS_DIR)/$$dep build/$$dep.ign build/$$dep-examples.ign ; \
		done; \
		run make install-config; \
		YQ_FILES="$$(if [ -f "overlay.bu" ]; then echo "- overlay.bu"; else echo "-"; fi)"; \
		echo "generate-butane-spec.sh build/$(PROJECT_NAME).bu"; \
		$(SCRIPTS_DIR)/generate-butane-spec.sh | yq eval-all '. as $$item ireduce ({}; . *+ $$item)' $$YQ_FILES > build/$(PROJECT_NAME).bu; \
		echo "generate-tarball.sh build/$(PROJECT_NAME).tar.gz"; \
		$(SCRIPTS_DIR)/generate-tarball.sh build/$(PROJECT_NAME).tar.gz; \
		(cat $(SCRIPTS_DIR)/butane.blocklist; echo; for file in $$(find "$$TARGET_CHROOT"); do echo "$${file#$$TARGET_CHROOT}"; done) | sort -u | grep -v -E '^$$' > "$(BUTANE_BLOCKLIST)"; \
		run make install-examples; \
		echo "generate-butane-spec.sh build/$(PROJECT_NAME)-examples.bu"; \
		$(SCRIPTS_DIR)/generate-butane-spec.sh build/$(PROJECT_NAME)-examples.bu; \
		(cat $(SCRIPTS_DIR)/butane.blocklist; echo; for file in $$(find "$$TARGET_CHROOT"); do echo "$${file#$$TARGET_CHROOT}"; done) | sort -u | grep -v -E '^$$' > "$(BUTANE_BLOCKLIST)"; \
	fi
.PHONY: build/$(PROJECT_NAME).bu build/$(PROJECT_NAME)-examples.bu

# Generate the current project's Ignition files from the Butane specs.
build/$(PROJECT_NAME).ign build/$(PROJECT_NAME)-examples.ign: %.ign: %.bu build
	butane --strict -o $@ $<

# Build the Butane specifications + Ignition files suitable for Fedora CoreOS, including those of the dependencies of this project.
package: build/$(PROJECT_NAME).tar.gz build/fcos-dev.ign build/fcos-test.ign

# Generate the local Butane spec + Ignition file (the one containing local customizations).
$(TOP_LEVEL_DIR)/build/local.ign: $(TOP_LEVEL_DIR)/local.bu
	mkdir -p $(TOP_LEVEL_DIR)/build
	butane --strict -o $@ $<

.INTERMEDIATE: build/fcos-dev.bu build/fcos-test.bu

# Generate the Butane specs for development and testing by merging the current project's spec with those of the dependencies.
# The development spec also includes the examples of the dependencies.
# Whereas the testing spec only includes the main specs of the dependencies.
build/fcos-dev.bu build/fcos-test.bu: DEPS := $(if $(filter-out base,$(PROJECT_NAME)),base $(DEPENDENCIES),$(DEPENDENCIES))
build/fcos-dev.bu: DEPS := $(DEPS) $(addsuffix -examples,$(DEPS))
build/fcos-dev.bu build/fcos-test.bu: %.bu: Makefile $(SCRIPTS_DIR)/default-butane-spec.sh build
	$(SCRIPTS_DIR)/default-butane-spec.sh $(PROJECT_NAME) $(DEPS) > $@

# Generate the final Fedora CoreOS ignition files (dev & test) by merging the Butane spec with the local and project-specific ignition files, as well as those of the dependencies.
build/fcos-dev.ign: $(TOP_LEVEL_DIR)/build/local.ign build/$(PROJECT_NAME).ign build/$(PROJECT_NAME)-examples.ign $(DEPENDENCIES_IGNITION_EXAMPLES_FILES)
build/fcos-test.ign: $(TOP_LEVEL_DIR)/build/local.ign build/$(PROJECT_NAME).ign $(DEPENDENCIES_IGNITION_FILES)
build/fcos-dev.ign build/fcos-test.ign: build/fcos-%.ign: build/fcos-%.bu build
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	tmp=$$(mktemp -d /tmp/butane-XXXXXX); \
	run cp $(filter %.ign,$^) $$tmp; \
	run butane --strict -d $$tmp -o $@ $<; \
	run rm -rf $$tmp

# Fetch the latest version of the Fedora CoreOS QCOW2 image.
/var/lib/libvirt/images/library/fedora-coreos.qcow2:
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	run mkdir -p /var/lib/libvirt/images/library/ ; \
	if ! run coreos-installer download -p qemu -f qcow2.xz -d -C /var/lib/libvirt/images/library/ ; then \
		echo "CoreOS QCOW2 image could not be downloaded." >&2; \
		exit 1; \
	fi ; \
	qcow2=$$(ls -1ctr /var/lib/libvirt/images/library/fedora-coreos-*.qcow2 | tail -n 1) ; \
	run mv "$$qcow2" $@

# Copy the ignition file.
/var/lib/libvirt/images/fcos-$(PROJECT_NAME)/fcos.ign: build/fcos-dev.ign
	install -D -o root -g root -m 0644 $< $@

# Copy the Fedora CoreOS base image to create a new QCOW2 image for the VM.
/var/lib/libvirt/images/fcos-$(PROJECT_NAME)/root.qcow2: /var/lib/libvirt/images/library/fedora-coreos.qcow2
	install -D -o root -g root -m 0644 $< $@

# Create an empty QCOW2 image for the /var filesystem of the VM.
/var/lib/libvirt/images/fcos-$(PROJECT_NAME)/var.qcow2:
	qemu-img create -f qcow2 $@ 100G

# Create the directory to be shared with the Fedora CoreOS VM through virtiofs.
/srv/fcos-$(PROJECT_NAME):
	install -d -o root -g root -m 0755 $@

# Launch a Fedora CoreOS VM with the generated Butane spec.
fcos-vm: pre-requisites clean-vm /var/lib/libvirt/images/fcos-$(PROJECT_NAME)/fcos.ign /var/lib/libvirt/images/fcos-$(PROJECT_NAME)/root.qcow2 /var/lib/libvirt/images/fcos-$(PROJECT_NAME)/var.qcow2 /srv/fcos-$(PROJECT_NAME)
	virt-install --name=fcos-$(PROJECT_NAME) --import --noautoconsole \
		--ram=4096 --vcpus=2 --os-variant=fedora-coreos-stable \
		--disk path=/var/lib/libvirt/images/fcos-$(PROJECT_NAME)/root.qcow2,format=qcow2,size=50 \
		--disk path=/var/lib/libvirt/images/fcos-$(PROJECT_NAME)/var.qcow2,format=qcow2 \
		--qemu-commandline="-fw_cfg name=opt/com.coreos/config,file=/var/lib/libvirt/images/fcos-$(PROJECT_NAME)/fcos.ign" \
		--network network=default,model=virtio \
		--console=pty,target.type=virtio --serial=pty --graphics=none --boot=uefi \
		--memorybacking=access.mode=shared,source.type=memfd \
		--filesystem=type=mount,accessmode=passthrough,driver.type=virtiofs,driver.queue=1024,source.dir=/srv/fcos-$(PROJECT_NAME),target.dir=data

# Clean up the Fedora CoreOS VM but keep its storage resources.
clean-vm: pre-requisites
	virsh destroy fcos-$(PROJECT_NAME) || true
	virsh undefine fcos-$(PROJECT_NAME) --nvram || true
	rm -f /var/lib/libvirt/images/fcos-$(PROJECT_NAME)/root.qcow2 /var/lib/libvirt/images/fcos-$(PROJECT_NAME)/fcos.ign

# Remove all resources related to the Fedora CoreOS VM.
remove-vm: clean-vm
	rm -rf /var/lib/libvirt/images/fcos-$(PROJECT_NAME)
	rm -rf /srv/fcos-$(PROJECT_NAME)

# Connect to the console of the Fedora CoreOS VM.
console: pre-requisites
	@set -Eeuo pipefail; \
	# Save the current terminal size to restore it after disconnecting from the VM console. \
	term_size=$$(stty size); \
	while sleep 2; do \
		virsh console fcos-$(PROJECT_NAME); \
		# Restore the terminal size after disconnecting from the VM console. \
		# This avoids issues with the terminal being stuck in an incorrect size because \
		# the UEFI / Grub TUI messed with the terminal size during a VM reboot. \
		eval $$(resize -s $$term_size); \
		echo -e "Disconnected. Reconnecting in 2 seconds...\nPress Ctrl-C to abort.\n"; \
	done

# List all systemd and quadlet unit names provided by the dependencies of this project.
units-pre::
	@for dep in $(DEPENDENCIES); do \
		$(MAKE) -s -C $(COOKBOOKS_DIR)/$$dep units 2>/dev/null; \
	done

# List all systemd and quadlet unit names provided by this project and, through "units-pre", also its dependencies.
units: units-pre
	@for unit in $(SYSTEMD_UNIT_NAMES) $(QUADLET_UNIT_NAMES); do echo "$$unit"; done

# List all dependencies of this project and also its transitive dependencies.
list-dependencies:
	@for dep in $(DEPENDENCIES); do \
		echo "$$dep"; \
		$(MAKE) -s -C $(COOKBOOKS_DIR)/$$dep list-dependencies 2>/dev/null; \
	done | sort -u

# Custom commands to be run before cleaning persistent data and configuration files.
# This target can be extended by Makefiles sourcing this one.
clean-pre::
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
    for dep in $(DEPENDENCIES); do \
		run $(MAKE) -C $(COOKBOOKS_DIR)/$$dep clean; \
	done

# Custom commands to be run after cleaning persistent data and configuration files.
# This target can be extended by Makefiles sourcing this one.
clean-post::

# Remove all persistent data and configuration files
clean: clean-pre pre-requisites
	rm -f build/$(PROJECT_NAME){,-examples}.bu build/*.ign
	@run() { echo $$*; "$$@"; }; \
	set -Eeuo pipefail; \
	if [ "$(I_KNOW_WHAT_I_AM_DOING)" != "yes" ]; then \
		read -p "This will remove all data of '$(PROJECT_NAME)'. Are you sure? (only 'yes' is accepted) " ans; \
		if [ "$$ans" != "yes" ] && [ "$$ans" != "YES" ]; then \
			echo "Aborted."; exit 1; \
		fi; \
	fi
	rm -rf /var/lib/quadlets/$(PROJECT_NAME)/ /run/quadlets/$(PROJECT_NAME)/ /etc/quadlets/$(PROJECT_NAME)/
	$(MAKE) clean-post

# All phony targets
.PHONY: all install install-config install-examples uninstall pre-requisites clean dryrun
.PHONY: tail-logs package help fcos-vm clean-vm console units units-pre remove-vm
.PHONY: clean-pre clean-post install-pre install-post uninstall-pre uninstall-post
.PHONY: install-files install-files-pre install-files-post install-actions
.PHONY: install-actions-pre install-actions-post pytest list-dependencies debug
