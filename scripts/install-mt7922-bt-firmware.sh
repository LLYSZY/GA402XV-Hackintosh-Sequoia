#!/bin/sh
# Install MediaTek MT7922 / AMD RZ616 Bluetooth RAM firmware into /etc/bluetool on macOS.
# Firmware binary is NOT bundled in this repository; obtain BT_RAM_CODE_MT7922_1_1_hdr.bin
# from upstream linux-firmware (mediatek/BT_RAM_CODE_MT7922_1_1_hdr.bin) or your hardware backup.
set -eu
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

EXPECTED_SHA256="299942dbec7d34af030670ea59f9f7b4fd5c64e738b9e0157d76f4dd3beb190f"
FW_NAME="BT_RAM_CODE_MT7922_1_1_hdr.bin"
ALLOW_CUSTOM=0
SRC=""

usage() {
    cat <<'EOF'
Usage: sudo ./scripts/install-mt7922-bt-firmware.sh [--allow-custom-sha256] [path/to/BT_RAM_CODE_MT7922_1_1_hdr.bin]

Options:
  --allow-custom-sha256   Allow installing a firmware file whose SHA-256 differs from the
                          tested GA402XV MT7922 firmware checksum (use with caution).
  -h, --help              Show this help message.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --allow-custom-sha256)
            ALLOW_CUSTOM=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [ -n "$SRC" ]; then
                printf 'Unexpected extra argument: %s\n' "$1" >&2
                usage >&2
                exit 2
            fi
            SRC="$1"
            shift
            ;;
    esac
done

[ -n "$SRC" ] || SRC="./$FW_NAME"

if [ "$(id -u)" -ne 0 ]; then
    printf 'Error: must run as root (use sudo).\n' >&2
    exit 1
fi

if [ ! -f "$SRC" ] || [ -L "$SRC" ]; then
    printf 'Error: firmware file not found or is a symlink: %s\n' "$SRC" >&2
    exit 1
fi

ACTUAL_SHA256=$(shasum -a 256 "$SRC" | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    if [ "$ALLOW_CUSTOM" -ne 1 ]; then
        printf 'Error: SHA-256 mismatch.\n  Expected: %s\n  Actual:   %s\n' "$EXPECTED_SHA256" "$ACTUAL_SHA256" >&2
        printf 'Pass --allow-custom-sha256 only if you have verified your firmware source.\n' >&2
        exit 1
    fi
    printf 'Warning: installing unverified custom firmware SHA-256: %s\n' "$ACTUAL_SHA256" >&2
fi

[ ! -L /etc/bluetool ] || { printf 'Error: /etc/bluetool is a symlink.\n' >&2; exit 1; }
[ ! -L "/etc/bluetool/$FW_NAME" ] || { printf 'Error: target file is a symlink.\n' >&2; exit 1; }

mkdir -p /etc/bluetool

if [ -f "/etc/bluetool/$FW_NAME" ] && cmp -s "$SRC" "/etc/bluetool/$FW_NAME"; then
    printf 'Firmware already installed and identical at /etc/bluetool/%s\n' "$FW_NAME"
    exit 0
fi

if [ -f "/etc/bluetool/$FW_NAME" ]; then
    BACKUP="/etc/bluetool/${FW_NAME}.before-ga402-$(date +%Y%m%d-%H%M%S)"
    cp -p "/etc/bluetool/$FW_NAME" "$BACKUP"
    printf 'Backed up existing firmware to %s\n' "$BACKUP"
fi

TMP=$(mktemp "/etc/bluetool/.ga402-fw.XXXXXX")
trap 'rm -f "$TMP"' EXIT

cp "$SRC" "$TMP"
chmod 644 "$TMP"
chown root:wheel "$TMP"
cmp -s "$SRC" "$TMP"
mv "$TMP" "/etc/bluetool/$FW_NAME"

printf 'Installed /etc/bluetool/%s (SHA-256: %s)\n' "$FW_NAME" "$ACTUAL_SHA256"
printf 'Reboot macOS for BlueToolFixup + ItlXhciKick to load the firmware.\n'
