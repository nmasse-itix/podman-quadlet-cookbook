# Lego renewal hooks
TARGET_LEGO_FILES = $(patsubst other/lego/%.sh, $(TARGET_CHROOT)/etc/quadlets/lego/renew-hooks.d/%.sh, $(wildcard other/lego/*.sh))
TARGET_FILES += $(TARGET_LEGO_FILES)
$(TARGET_CHROOT)/etc/quadlets/lego/renew-hooks.d/%.sh: other/lego/%.sh
	install -D -m 0755 -o root -g root $< $@
