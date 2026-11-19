#!/bin/sh
# Gera a ISO da LumeOS. Rode como root em Debian ou Ubuntu (ou em um container Debian privilegiado).
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root: sudo ./build.sh" >&2
    exit 1
fi

cd "$(dirname "$0")"

apt-get update
apt-get install -y live-build debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools

chmod +x auto/config config/hooks/live/*.chroot config/includes.chroot/usr/local/bin/*
lb clean --purge || true
lb config
lb build 2>&1 | tee build.log

ls -lh ./*.iso
echo "ISO pronta. Teste primeiro em uma VM (QEMU, VirtualBox ou VMware) com EFI ativado."
