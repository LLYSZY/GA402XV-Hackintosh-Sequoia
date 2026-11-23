#!/bin/sh
# Read-only hardware visibility & display-latch check for ASUS ROG Zephyrus G14 GA402XV.
# Prints only public PCI vendor/device IDs and display-latch sysctl state.
set -eu

tree=$(ioreg -r -c IOPCIDevice -l -w0)
if ! printf '%s\n' "$tree" | grep -F '"vendor-id"' >/dev/null; then
    printf 'note: IORegistry device properties are unavailable (sandboxed environment?); run in a normal terminal.\n' >&2
fi
for id in pci1002,15bf pci10de,28e0; do
    if printf '%s\n' "$tree" | grep -F "$id" >/dev/null; then
        printf '%s: visible\n' "$id"
    else
        printf '%s: not enumerated\n' "$id"
    fi
done

if latch=$(sysctl -n debug.nvrmfb_flip_latch 2>/dev/null); then
    printf 'debug.nvrmfb_flip_latch: %s\n' "$latch"
else
    printf 'debug.nvrmfb_flip_latch: unavailable\n'
fi
