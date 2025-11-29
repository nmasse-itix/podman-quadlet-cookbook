.PHONY: all install uninstall pre-requisites clean dryrun

PROJECT_NAME := $(shell basename "$${PWD}")
QUADLETS_FILES = $(wildcard *.container *.volume *.network *.pod *.build)
SYSTEMD_FILES = $(wildcard *.service *.target *.timer)
SYSTEMD_UNIT_NAMES := $(wildcard *.service *.target *.timer)
SYSTEMD_MAIN_UNIT_NAMES := $(wildcard *.target)
QUADLET_UNIT_NAMES := $(patsubst %.container, %.service, $(wildcard *.container)) \
					 $(patsubst %.volume, %-volume.service, $(wildcard *.volume)) \
					 $(patsubst %.network, %-network.service, $(wildcard *.network)) \
					 $(patsubst %.pod, %-pod.service, $(wildcard *.pod)) \
					 $(patsubst %.build, %-build.service, $(wildcard *.build))
CONFIG_FILES = $(wildcard config/*)
TARGET_QUADLETS_FILES = $(addprefix /etc/containers/systemd/, $(QUADLETS_FILES))
TARGET_SYSTEMD_FILES = $(addprefix /etc/systemd/system/, $(SYSTEMD_FILES))
TARGET_CONFIG_FILES = $(patsubst config/%, /etc/quadlets/$(PROJECT_NAME)/%, $(CONFIG_FILES))

pre-requisites:
	@test "$$(id -u)" -eq 0 || (echo "This Makefile must be run as root" >&2; exit 1)

all: install

dryrun:
	QUADLET_UNIT_DIRS="$$PWD" /usr/lib/systemd/system-generators/podman-system-generator -dryrun > /dev/null

/etc/containers/systemd/%.container: %.container
	install -D -m 0644 -o root -g root $< $@

/etc/containers/systemd/%.volume: %.volume
	install -D -m 0644 -o root -g root $< $@

/etc/containers/systemd/%.network: %.network
	install -D -m 0644 -o root -g root $< $@

/etc/containers/systemd/%.pod: %.pod
	install -D -m 0644 -o root -g root $< $@

/etc/containers/systemd/%.build: %.build
	install -D -m 0644 -o root -g root $< $@

/etc/systemd/system/%.service: %.service
	install -D -m 0644 -o root -g root $< $@

/etc/systemd/system/%.target: %.target
	install -D -m 0644 -o root -g root $< $@

/etc/systemd/system/%.timer: %.timer
	install -D -m 0644 -o root -g root $< $@

/etc/quadlets/$(PROJECT_NAME)/%: config/%
	install -D -m 0644 -o root -g root $< $@

install: pre-requisites dryrun $(TARGET_QUADLETS_FILES) $(TARGET_SYSTEMD_FILES) $(TARGET_CONFIG_FILES)
	systemctl daemon-reload
	systemd-analyze --generators=true verify $(QUADLET_UNIT_NAMES) $(SYSTEMD_UNIT_NAMES)
	systemctl enable $(SYSTEMD_UNIT_NAMES)
	systemctl start $(SYSTEMD_MAIN_UNIT_NAMES)

uninstall: pre-requisites
	systemctl --no-block disable $(SYSTEMD_UNIT_NAMES) || true
	systemctl --no-block stop $(SYSTEMD_UNIT_NAMES) $(QUADLET_UNIT_NAMES) || true
	rm -f $(TARGET_QUADLETS_FILES) $(TARGET_SYSTEMD_FILES) $(TARGET_CONFIG_FILES)
	systemctl daemon-reload

clean:
	rm -rf /var/lib/quadlets/$(PROJECT_NAME)/ /etc/quadlets/$(PROJECT_NAME)/
