# Mosquitto configuration fragments
# This hook lets a dependent cookbook drop a configuration fragment into the broker's
# include_dir by placing a file named other/mosquitto/<name>.conf in its own directory.
# It lands in /etc/quadlets/mosquitto/conf.d/<name>.conf and is loaded by mosquitto.

# Define the target files deployed to the target system when the hook is used by a
# dependent cookbook.
TARGET_MOSQUITTO_FILES = $(patsubst other/mosquitto/%.conf, $(TARGET_CHROOT)/etc/quadlets/mosquitto/conf.d/%.conf, $(wildcard other/mosquitto/*.conf))

# Those fragments are examples for the dependent cookbooks and thus are not part of the
# final package.
TARGET_EXAMPLE_FILES += $(TARGET_MOSQUITTO_FILES)

# Define the installation rule for the target files. Owned by the broker user so it can
# read them (they are mounted read-only into the container).
$(TARGET_CHROOT)/etc/quadlets/mosquitto/conf.d/%.conf: other/mosquitto/%.conf
	install -D -m 0644 -o 10033 -g 10000 $< $@
