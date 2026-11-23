#!/usr/bin/env python3
"""
Inspect and prepare Apple's x86_64 UEFI boot.efi for UEFI Secure Boot signing.

Why this exists:
1. When OpenCore's FixupAppleEfiImages=True runs at boot, it removes the executable
   flag (IMAGE_SCN_MEM_EXECUTE, 0x20000000) from Apple boot.efi's `.data` section,
   which invalidates any UEFI Secure Boot signature computed before the fixup.
   Pre-applying that W^X adjustment before signing keeps firmware verification valid.
2. Apple's Sequoia boot.efi can contain an unallocated zero-filled gap between `.data`'s
   SizeOfRawData and the start of `.reloc` (because VirtualSize > SizeOfRawData).
   osslsigncode computes a linear Authenticode hash across the file, whereas EDK2's
   DxeImageVerificationLib hashes PE headers, sorted sections (each SizeOfRawData bytes),
   and trailing bytes — causing the two digests to diverge unless `.data`'s SizeOfRawData
   is extended to cover the existing zero padding up to VirtualSize / next section.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
from dataclasses import dataclass
from typing import List, Tuple

IMAGE_SCN_MEM_EXECUTE = 0x20000000
PE32PLUS_MAGIC = 0x20B
AMD64_MACHINE = 0x8664


@dataclass
class SectionInfo:
    index: int
    header_off: int
    name: str
    virtual_size: int
    virtual_addr: int
    size_of_raw_data: int
    pointer_to_raw_data: int
    characteristics: int


@dataclass
class PeLayout:
    e_lfanew: int
    coff_off: int
    opt_off: int
    size_of_headers: int
    checksum_off: int
    checksum: int
    sec_dir_off: int
    cert_off: int
    cert_size: int
    sections: List[SectionInfo]


def parse_pe32plus(data: bytes) -> PeLayout:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("Not a valid MZ/PE binary.")

    (e_lfanew,) = struct.unpack_from("<I", data, 0x3C)
    if e_lfanew + 24 > len(data) or data[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
        raise ValueError("Missing PE signature.")

    coff_off = e_lfanew + 4
    machine, num_sections, _, _, _, size_of_opt, _ = struct.unpack_from("<HHIIIHH", data, coff_off)
    if machine != AMD64_MACHINE:
        raise ValueError(f"Unsupported PE machine 0x{machine:04x}; expected 0x{AMD64_MACHINE:04x} (x86_64).")

    opt_off = coff_off + 20
    if opt_off + size_of_opt > len(data) or size_of_opt < 112:
        raise ValueError("Optional header truncated or too small for PE32+.")

    (magic,) = struct.unpack_from("<H", data, opt_off)
    if magic != PE32PLUS_MAGIC:
        raise ValueError(f"Unsupported OptionalHeader Magic 0x{magic:04x}; expected PE32+ (0x{PE32PLUS_MAGIC:04x}).")

    (size_of_headers,) = struct.unpack_from("<I", data, opt_off + 60)
    checksum_off = opt_off + 64
    (checksum,) = struct.unpack_from("<I", data, checksum_off)
    (num_rva_and_sizes,) = struct.unpack_from("<I", data, opt_off + 108)
    if num_rva_and_sizes < 5 or size_of_opt < 112 + 5 * 8:
        raise ValueError("PE OptionalHeader lacks Security Directory entry.")

    sec_dir_off = opt_off + 112 + 4 * 8
    cert_off, cert_size = struct.unpack_from("<II", data, sec_dir_off)

    sec_table_off = opt_off + size_of_opt
    if sec_table_off + num_sections * 40 > len(data):
        raise ValueError("Section table extends past EOF.")

    sections: List[SectionInfo] = []
    for i in range(num_sections):
        hoff = sec_table_off + i * 40
        raw_name = data[hoff : hoff + 8]
        name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        vsize, vaddr, sraw, praw, _, _, _, _, chars = struct.unpack_from("<IIIIIIHHI", data, hoff + 8)
        sections.append(
            SectionInfo(
                index=i,
                header_off=hoff,
                name=name,
                virtual_size=vsize,
                virtual_addr=vaddr,
                size_of_raw_data=sraw,
                pointer_to_raw_data=praw,
                characteristics=chars,
            )
        )

    return PeLayout(
        e_lfanew=e_lfanew,
        coff_off=coff_off,
        opt_off=opt_off,
        size_of_headers=size_of_headers,
        checksum_off=checksum_off,
        checksum=checksum,
        sec_dir_off=sec_dir_off,
        cert_off=cert_off,
        cert_size=cert_size,
        sections=sections,
    )


def compute_pe_checksum(data: bytes, checksum_off: int) -> int:
    buf = bytearray(data)
    buf[checksum_off : checksum_off + 4] = b"\x00\x00\x00\x00"
    if len(buf) % 2 == 1:
        buf.append(0)
    total = 0
    for i in range(0, len(buf), 2):
        total += buf[i] | (buf[i + 1] << 8)
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (total + len(data)) & 0xFFFFFFFF


def compute_linear_authenticode_sha256(data: bytes, pe: PeLayout) -> str:
    h = hashlib.sha256()
    h.update(data[: pe.checksum_off])
    h.update(data[pe.checksum_off + 4 : pe.sec_dir_off])
    body_start = pe.sec_dir_off + 8
    if pe.cert_size > 0 and pe.cert_off > 0:
        if pe.cert_off < body_start or pe.cert_off + pe.cert_size > len(data):
            raise ValueError("Invalid Security Directory bounds.")
        h.update(data[body_start : pe.cert_off])
        h.update(data[pe.cert_off + pe.cert_size :])
    else:
        h.update(data[body_start:])
    return h.hexdigest()


def compute_edk2_authenticode_sha256(data: bytes, pe: PeLayout) -> str:
    """Replicate EDK2 DxeImageVerificationLib HashPeImage() SHA-256 calculation."""
    h = hashlib.sha256()
    h.update(data[: pe.checksum_off])
    h.update(data[pe.checksum_off + 4 : pe.sec_dir_off])
    h.update(data[pe.sec_dir_off + 8 : pe.size_of_headers])

    sum_hashed = pe.size_of_headers
    non_empty = [s for s in pe.sections if s.size_of_raw_data > 0]
    for sec in sorted(non_empty, key=lambda s: s.pointer_to_raw_data):
        end = sec.pointer_to_raw_data + sec.size_of_raw_data
        if end > len(data):
            raise ValueError(f"Section {sec.name} extends past EOF.")
        h.update(data[sec.pointer_to_raw_data : end])
        sum_hashed += sec.size_of_raw_data

    image_size_without_cert = len(data) - pe.cert_size if (pe.cert_size > 0 and pe.cert_off > 0) else len(data)
    if image_size_without_cert > sum_hashed:
        tail_len = image_size_without_cert - sum_hashed
        h.update(data[sum_hashed : sum_hashed + tail_len])
    return h.hexdigest()


def print_report(path: str, data: bytes, pe: PeLayout) -> Tuple[str, str]:
    lin = compute_linear_authenticode_sha256(data, pe)
    edk = compute_edk2_authenticode_sha256(data, pe)
    calc_sum = compute_pe_checksum(data, pe.checksum_off)
    print(f"File: {path} ({len(data)} bytes)")
    print(f"CheckSum: stored=0x{pe.checksum:08x}, computed=0x{calc_sum:08x}")
    print(f"SecurityDir: offset=0x{pe.cert_off:x}, size={pe.cert_size}")
    print("Sections:")
    prev_end = pe.size_of_headers
    gaps: List[str] = []
    for s in sorted(pe.sections, key=lambda x: x.pointer_to_raw_data):
        raw_end = s.pointer_to_raw_data + s.size_of_raw_data
        if s.size_of_raw_data > 0 and s.pointer_to_raw_data > prev_end:
            gaps.append(f"0x{prev_end:x}..0x{s.pointer_to_raw_data:x} ({s.pointer_to_raw_data - prev_end} bytes before {s.name})")
        if raw_end > prev_end:
            prev_end = raw_end
        wx = " [EXEC]" if (s.characteristics & IMAGE_SCN_MEM_EXECUTE) else ""
        print(
            f"  {s.name:8s} VSize={s.virtual_size:6d} RawOff=0x{s.pointer_to_raw_data:06x} "
            f"RawSize={s.size_of_raw_data:6d} RawEnd=0x{raw_end:06x} Chars=0x{s.characteristics:08x}{wx}"
        )
    if gaps:
        print("Unallocated raw gaps:")
        for g in gaps:
            print(f"  - {g}")
    print(f"Linear Authenticode SHA-256: {lin}")
    print(f"EDK2   Authenticode SHA-256: {edk}")
    print(f"Digests match: {'YES' if lin == edk else 'NO (MISMATCH!)'}")
    return lin, edk


def patch_pe(data: bytes) -> Tuple[bytes, List[str]]:
    pe = parse_pe32plus(data)
    if pe.cert_off != 0 or pe.cert_size != 0:
        raise ValueError("Input PE already has an Authenticode signature; patch an unsigned boot.efi before signing.")

    buf = bytearray(data)
    changes: List[str] = []

    data_sec = next((s for s in pe.sections if s.name == ".data"), None)
    if data_sec is None:
        raise ValueError("No .data section found in PE image.")

    if data_sec.characteristics & IMAGE_SCN_MEM_EXECUTE:
        new_chars = data_sec.characteristics & ~IMAGE_SCN_MEM_EXECUTE
        struct.pack_into("<I", buf, data_sec.header_off + 36, new_chars)
        changes.append(f".data Characteristics: 0x{data_sec.characteristics:08x} -> 0x{new_chars:08x} (cleared EXEC)")

    if data_sec.virtual_size > data_sec.size_of_raw_data:
        raw_end = data_sec.pointer_to_raw_data + data_sec.size_of_raw_data
        later_starts = [
            s.pointer_to_raw_data
            for s in pe.sections
            if s.size_of_raw_data > 0 and s.pointer_to_raw_data >= raw_end
        ]
        limit_end = min(later_starts) if later_starts else len(buf)
        target_end = min(data_sec.pointer_to_raw_data + data_sec.virtual_size, limit_end)
        if target_end > raw_end:
            gap = buf[raw_end:target_end]
            if any(b != 0 for b in gap):
                raise ValueError(
                    f"Refusing to extend .data SizeOfRawData: {len(gap)}-byte gap "
                    f"[0x{raw_end:x}:0x{target_end:x}] contains non-zero bytes."
                )
            new_raw_size = target_end - data_sec.pointer_to_raw_data
            struct.pack_into("<I", buf, data_sec.header_off + 16, new_raw_size)
            changes.append(
                f".data SizeOfRawData: {data_sec.size_of_raw_data} -> {new_raw_size} "
                f"(covered {len(gap)}-byte zero gap)"
            )

    new_sum = compute_pe_checksum(bytes(buf), pe.checksum_off)
    struct.pack_into("<I", buf, pe.checksum_off, new_sum)
    changes.append(f"PE CheckSum updated: 0x{new_sum:08x}")

    patched = bytes(buf)
    pe_after = parse_pe32plus(patched)
    lin = compute_linear_authenticode_sha256(patched, pe_after)
    edk = compute_edk2_authenticode_sha256(patched, pe_after)
    if lin != edk:
        raise RuntimeError(f"Post-patch linear vs EDK2 Authenticode SHA-256 still mismatch ({lin} != {edk}).")

    return patched, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or patch unsigned Apple boot.efi PE32+ layout for UEFI Secure Boot.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", metavar="FILE", help="Inspect PE sections and compare linear vs EDK2 Authenticode SHA-256.")
    mode.add_argument("--patch", metavar="INPUT", help="Patch unsigned INPUT boot.efi (requires --output).")
    parser.add_argument("--output", metavar="OUTPUT", help="Output path for --patch (must differ from INPUT).")
    args = parser.parse_args()

    if args.inspect:
        with open(args.inspect, "rb") as f:
            data = f.read()
        pe = parse_pe32plus(data)
        lin, edk = print_report(args.inspect, data, pe)
        return 0 if lin == edk else 2

    if not args.output:
        parser.error("--patch requires --output")
    if os.path.abspath(args.patch) == os.path.abspath(args.output):
        parser.error("--output must be a separate file path from --patch INPUT (keep a verified backup).")

    with open(args.patch, "rb") as f:
        orig = f.read()
    patched, changes = patch_pe(orig)
    with open(args.output, "wb") as f:
        f.write(patched)

    print("Applied patches:")
    for c in changes:
        print(f"  - {c}")
    pe_after = parse_pe32plus(patched)
    print_report(args.output, patched, pe_after)
    return 0


if __name__ == "__main__":
    sys.exit(main())
