# Traefik configuration files
TARGET_TRAEFIK_FILES = $(patsubst other/traefik/%, $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%, $(wildcard other/traefik/*))
TARGET_EXAMPLE_FILES += $(TARGET_TRAEFIK_FILES)
$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%: other/traefik/%
	install -m 0644 -o 10001 -g 10000 $< $@
