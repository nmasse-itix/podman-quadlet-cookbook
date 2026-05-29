# Nftables configuration files
TARGET_NFTABLES_FILES = $(patsubst other/nftables/%, $(TARGET_CHROOT)/etc/quadlets/nftables/%, $(wildcard other/nftables/*))
TARGET_EXAMPLE_FILES += $(TARGET_NFTABLES_FILES)
$(TARGET_CHROOT)/etc/quadlets/nftables/%: other/nftables/%
	install -m 0644 -o root -g root $< $@
