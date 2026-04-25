#!/bin/bash

set -u

for vm in $(virsh list --name); do 
    virsh destroy $vm
    virsh undefine --nvram $vm
    rm -rf "/var/lib/libvirt/images/$vm"
done

rm -rf /srv/pebble /srv/fcos-test-*
podman stop -i pebble-acme-server
podman rm -fi pebble-acme-server

virsh net-dumpxml default | grep -oP '(?<=<host ip=)"[^"]*' | xargs -I {} virsh net-update default delete dns-host "<host ip="{}" />" --live --config
virsh net-destroy default
virsh net-start default
