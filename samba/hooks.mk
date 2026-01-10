# Samba configuration files
TARGET_SAMBA_FILES = $(patsubst other/samba/%, $(TARGET_CHROOT)/etc/quadlets/samba/smb.conf.d/%, $(wildcard other/samba/*))
TARGET_EXAMPLE_FILES += $(TARGET_SAMBA_FILES)
$(TARGET_CHROOT)/etc/quadlets/samba/smb.conf.d/%: other/samba/%
	install -m 0644 -o root -g root $< $@
