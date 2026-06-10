# Tools installation scripts
TARGET_INSTALL_TOOLS_FILES = $(patsubst other/base/install-tools.d/%, $(TARGET_CHROOT)/etc/quadlets/base/install-tools.d/%, $(wildcard other/base/install-tools.d/*))
TARGET_EXAMPLE_FILES += $(TARGET_INSTALL_TOOLS_FILES)
$(TARGET_CHROOT)/etc/quadlets/base/install-tools.d/%.sh: other/base/install-tools.d/%.sh
	install -m 0755 -o root -g root $< $@
