#!/bin/sh
# Audit the repository before publishing to ensure no SMBIOS, keys, paths, or binaries leak.
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FAIL=0

fail() {
    printf '[FAIL] %s\n' "$1" >&2
    FAIL=1
}

pass() {
    printf '[PASS] %s\n' "$1"
}

cd "$REPO_ROOT"

# 1. Forbidden sensitive or binary files
FORBIDDEN_FILES=$(find . -path './.git' -prune -o \
    \( -name '*.key' -o -name '*.pem' -o -name '*.cer' -o -name '*.crt' -o -name '*.esl' \
       -o -name '*.p12' -o -name '*.pfx' -o -name '*.efi' -o -name '*.bin' -o -name '*.kc' \
       -o -name '.DS_Store' -o -name '._*' -o -name 'config.plist' \) -print)
if [ -n "$FORBIDDEN_FILES" ]; then
    printf '%s\n' "$FORBIDDEN_FILES" >&2
    fail "Forbidden key, cert, binary, metadata, or live config.plist files found."
else
    pass "No forbidden key, certificate, EFI/firmware binary, or metadata files present."
fi

FORBIDDEN_KEXTS=$(find . -path './.git' -prune -o -type d -name '*.kext' -print)
if [ -n "$FORBIDDEN_KEXTS" ]; then
    printf '%s\n' "$FORBIDDEN_KEXTS" >&2
    fail "Bundled .kext directories found."
else
    pass "No third-party .kext binaries bundled."
fi

# 2. Sensitive content patterns (exclude .git and this audit script itself)
SCAN_FILES=$(find . -path './.git' -prune -o -path './scripts/audit-sensitive-data.sh' -prune -o -type f ! -name '*.aml' -print)

if [ -n "$SCAN_FILES" ]; then
    # Private keys / certificates
    if printf '%s\n' "$SCAN_FILES" | xargs grep -nE -- '-----BEGIN ([A-Z ]+)?(PRIVATE KEY|CERTIFICATE)-----' 2>/dev/null; then
        fail "PEM private key or certificate block found."
    else
        pass "No PEM private key or certificate blocks found."
    fi

    # Tokens
    if printf '%s\n' "$SCAN_FILES" | xargs grep -nE -- '(gh[pousr]_[A-Za-z0-9_]{10,}|github_pat_[A-Za-z0-9_]{10,})' 2>/dev/null; then
        fail "Token-like secret pattern found."
    else
        pass "No GitHub token patterns found."
    fi

    # Personal home paths (allow generic placeholder documentation if explicitly <user> or yourname)
    USER_HITS=$(printf '%s\n' "$SCAN_FILES" | xargs grep -nE -- '(/Users/[A-Za-z0-9._-]+|[A-Za-z]:[/\\]Users[/\\][A-Za-z0-9._-]+)' 2>/dev/null | grep -vE '(<username>|<user>|yourname)' || true)
    if [ -n "$USER_HITS" ]; then
        printf '%s\n' "$USER_HITS" >&2
        fail "Personal home directory path found."
    else
        pass "No personal home directory paths found."
    fi
fi

# 3. Verify config.sample.plist placeholders (must not contain real SMBIOS values)
if [ -f "EFI-template/OC/config.sample.plist" ]; then
    python3 - <<'PY' || FAIL=1
import plistlib, sys
with open("EFI-template/OC/config.sample.plist", "rb") as f:
    cfg = plistlib.load(f)
gen = cfg["PlatformInfo"]["Generic"]
assert gen["SystemSerialNumber"] == "W00000000001", f"Unexpected serial: {gen['SystemSerialNumber']}"
assert gen["MLB"] == "M0000000000000001", f"Unexpected MLB: {gen['MLB']}"
assert gen["SystemUUID"] == "00000000-0000-0000-0000-000000000000", f"Unexpected UUID: {gen['SystemUUID']}"
assert gen["ROM"] == bytes.fromhex("112233000000"), f"Unexpected ROM: {gen['ROM'].hex()}"
print("[PASS] config.sample.plist PlatformInfo.Generic contains safe placeholder values.")
PY
else
    fail "Missing EFI-template/OC/config.sample.plist."
fi

# 4. Optional ocvalidate check
OCVALIDATE="${OCVALIDATE_BIN:-}"
if [ -z "$OCVALIDATE" ] && command -v ocvalidate >/dev/null 2>&1; then
    OCVALIDATE=$(command -v ocvalidate)
fi
if [ -n "$OCVALIDATE" ] && [ -x "$OCVALIDATE" ]; then
    if "$OCVALIDATE" "EFI-template/OC/config.sample.plist" >/dev/null; then
        pass "ocvalidate passed on EFI-template/OC/config.sample.plist."
    else
        fail "ocvalidate failed on EFI-template/OC/config.sample.plist."
    fi
else
    printf '[INFO] ocvalidate binary not set (set OCVALIDATE_BIN=/path/to/ocvalidate to enable).\n'
fi

if [ "$FAIL" -ne 0 ]; then
    printf 'Audit FAILED.\n' >&2
    exit 1
fi
printf 'Audit PASSED cleanly.\n'
