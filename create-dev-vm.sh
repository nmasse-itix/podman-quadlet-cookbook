#!/bin/bash
set -Eeuo pipefail

# Script to create a Fedora Server VM with cloud-init
# Specs: 16GB RAM, 4 vCPU, 1TB sparse root disk

# Configuration
VM_NAME="${VM_NAME:-quadlets}"
VM_RAM="${VM_RAM:-16384}"  # Unit: MB
VM_VCPUS="${VM_VCPUS:-4}"
DISK_SIZE="${DISK_SIZE:-1024}"  # Unit: GB
LIBVIRT_IMAGES_DIR="/var/lib/libvirt/images"
VM_DIR="${LIBVIRT_IMAGES_DIR}/${VM_NAME}"
CLOUD_INIT_CONFIG="$(dirname "$(realpath "$0")")/cloud-init.dev.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root or with sudo"
   exit 1
fi

# Check required commands
for cmd in virt-install genisoimage curl jq; do
    if ! command -v "$cmd" &> /dev/null; then
        log_error "Required command '$cmd' not found. Please install it first."
        exit 1
    fi
done

# Check if cloud-init config exists
if [[ ! -f "$CLOUD_INIT_CONFIG" ]]; then
    log_error "Cloud-init config not found: $CLOUD_INIT_CONFIG"
    exit 1
fi

# Get the latest Fedora Server version
log_info "Determining latest Fedora Server version..."
FEDORA_VERSION=$(curl -sSfL https://fedoraproject.org/releases.json | \
    jq -r '.[] | select(.variant=="Cloud") | .version' | \
    sort -rV | \
    head -n 1)

if [[ -z "$FEDORA_VERSION" ]]; then
    log_error "Could not determine latest Fedora version!"
    exit 1
fi

log_info "Using Fedora Server version: $FEDORA_VERSION"

# Get download URL from releases.json
log_info "Fetching download information..."
QCOW2_FULL_URL=$(curl -sSfL https://fedoraproject.org/releases.json | \
    jq -r --arg ver "$FEDORA_VERSION" --arg arch "$(arch)" \
    '.[] | select(.version==$ver and .variant=="Cloud" and .subvariant=="Cloud_Base" and .arch==$arch and (.link|endswith(".qcow2"))) | .link')

if [[ -z "$QCOW2_FULL_URL" ]]; then
    log_error "Could not find Qcow2 download URL for Fedora $FEDORA_VERSION"
    exit 1
fi

QCOW2_FILENAME=$(basename "$QCOW2_FULL_URL")
mkdir -p "$VM_DIR"

# Download Qcow2 image if not already present
QCOW2_PATH="${VM_DIR}/${QCOW2_FILENAME}"
if [[ -f "$QCOW2_PATH" ]]; then
    log_info "Qcow2 image already exists: $QCOW2_PATH"
else
    log_info "Downloading Qcow2 image..."
    curl -fL -o "$QCOW2_PATH" "$QCOW2_FULL_URL"
    log_info "Download complete"
fi

# Create the VM disk from the base image
VM_DISK="${VM_DIR}/${VM_NAME}.qcow2"
if [[ -f "$VM_DISK" ]]; then
    log_warn "VM disk already exists: $VM_DISK"
else
    log_info "Creating VM disk (${DISK_SIZE}GB sparse)..."
    qemu-img create -f qcow2 -F qcow2 -b "$QCOW2_PATH" "$VM_DISK" "${DISK_SIZE}G"
fi

# Create cloud-init ISO
CLOUD_INIT_ISO="${VM_DIR}/cloud-init.iso"
USER_DATA="${VM_DIR}/user-data"
META_DATA="${VM_DIR}/meta-data"

log_info "Creating cloud-init configuration files..."

# Copy user-data from cloud-init config
cp "$CLOUD_INIT_CONFIG" "$USER_DATA"

# Create meta-data file
cat > "$META_DATA" << EOF
instance-id: ${VM_NAME}
local-hostname: ${VM_NAME}
EOF

log_info "Creating cloud-init ISO..."
genisoimage -output "$CLOUD_INIT_ISO" -volid cidata -joliet -rock "$USER_DATA" "$META_DATA"

# Check if VM already exists
if virsh dominfo "$VM_NAME" &> /dev/null; then
    log_warn "VM '$VM_NAME' already exists"
else
    # Create the VM
    log_info "Creating VM: $VM_NAME"
    log_info "  RAM: ${VM_RAM}MB (16GB)"
    log_info "  vCPUs: $VM_VCPUS"
    log_info "  Disk: ${DISK_SIZE}GB (sparse)"

    virt-install \
        --name "$VM_NAME" \
        --ram "$VM_RAM" \
        --vcpus "$VM_VCPUS" \
        --cpu host-passthrough \
        --disk path="$VM_DISK",format=qcow2,bus=virtio \
        --disk path="$CLOUD_INIT_ISO",device=cdrom \
        --os-variant fedora-unknown \
        --network network=default,model=virtio \
        --graphics none \
        --console pty,target.type=virtio \
        --serial pty \
        --sysinfo system.serial=ds=nocloud \
        --boot uefi \
        --import \
        --noautoconsole

    log_info "VM '$VM_NAME' created successfully!"
    log_info ""
    log_info "VM Details:"
    log_info "  Name: $VM_NAME"
    log_info "  Directory: $VM_DIR"
    log_info "  Disk: $VM_DISK"
    log_info "  Cloud-init: $CLOUD_INIT_ISO"
    log_info ""
    log_info "To start the VM: virsh start $VM_NAME"
    log_info "To connect to console: virsh console $VM_NAME"
    log_info "To get IP address: virsh domifaddr $VM_NAME"
    log_info "To destroy the VM: virsh destroy $VM_NAME"
    log_info "To delete the VM: virsh undefine --nvram $VM_NAME && rm -rf $VM_DIR"
fi

