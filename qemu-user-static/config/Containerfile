FROM quay.io/fedora/fedora:42

RUN dnf install -y qemu-user-static \
 && dnf clean all

ADD container-entrypoint /

ENTRYPOINT ["/container-entrypoint"]
CMD []
