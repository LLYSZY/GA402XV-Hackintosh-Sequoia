# ASUS ROG Zephyrus G14 GA402XV (2023) · macOS Sequoia

[中文](README.md) | **English**

An open-source, fully sanitized Hackintosh reference repository and post-install toolkit for the **ASUS ROG Zephyrus G14 GA402XV (2023)** running **macOS Sequoia 15.8.1 (Build 24H32)** with **OpenCore 1.0.9**.

> **Tested Baseline**: macOS Sequoia **15.8.1 (24H32)** · OpenCore **1.0.9** · SMBIOS **`MacBookPro16,2`**  
> **Hardware**: AMD Ryzen 9 7940HS · NVIDIA GeForce RTX 4060 Laptop (primary display path) / Radeon 780M · MediaTek MT7922 (RZ616) · Realtek ALC285 + I²C CS35L41

> [!IMPORTANT]
> This repository distributes **no** copyrighted macOS files, proprietary firmware blobs, prebuilt third-party `.kext`/`.efi` binaries, personal SMBIOS identifiers, or Secure Boot private keys.

---

## Hardware Compatibility Summary

| Subsystem | Component / Driver Stack | Status | Observed Behavior |
| --- | --- | :---: | --- |
| **CPU & Power** | Ryzen 9 7940HS + 27 AMD Kernel Patches + `AMDRyzenCPUPowerManagement` + `ForgedInvariant` | ✅ Working | 8-core topology, TSC sync, and CPU branding active |
| **dGPU & High Refresh** | RTX 4060 Laptop (`10DE:28E0`) + **NullMoth 2.9** | ✅ Working | Internal eDP 2560×1600 @ 165 Hz; HDMI verified up to 4K @ 120 Hz; `debug.nvrmfb_flip_latch=2` cuts 10s mean flip wait from `2732 µs` to `249 µs`; 180-frame H.264 `NVDEC` sample decoded with 0 errors |
| **Trackpad & Keyboard** | I²C Touchpad (`VoodooI2C` 2.9.1 `-vi2c-force-polling`) + `VoodooPS2Controller` | ✅ Working | Cursor teleportation eliminated after disabling Force Touch simulation in macOS Trackpad settings |
| **Wi-Fi** | RZ616 / MT7922 (`14C3:0616`) + `YYavicWiFi 0.7.2` | ✅ Working | Connects via native macOS Wi-Fi menu |
| **Bluetooth** | MT7922 (`0489:E0F6`) + `BlueToolFixup` + `ItlXhciKick` + `/etc/bluetool` firmware | ⚠️ Basic OK | Toggle and pairing work; AirDrop / Continuity unverified |
| **Audio** | Realtek ALC285 + I²C CS35L41 (`1043:1463`, `layout-id=31`) | ⚠️ Limited | Built-in speakers play audio but sound thin (missing I²C woofer amp init); tested USB-C speaker exhibits `OutputFellBehind` |
| **UEFI Secure Boot** | Preserved Microsoft CAs + Self-signed OpenCore + Preboot `boot.efi` PE fix | ⚠️ Boots macOS | Boots macOS 15.8.1 with firmware `SecureBoot=1`; requires re-signing `boot.efi` after macOS updates; Windows game anti-cheat runtime not verified |
| **Radeon 780M iGPU** | `1002:15BF` + `nullarc` Sequoia timer port | 🧪 Experimental | `PhxBringup` + `PhxAccel` link into 24H32 AuxKC and unit tests pass; disabled by `disable-gpu` in live EFI, runtime iGPU desktop/power unverified |

---

## Quick Start

1. Download **OpenCore 1.0.9** and the exact kexts listed in [`docs/KEXTS-AND-DRIVERS.md`](docs/KEXTS-AND-DRIVERS.md) from their upstream repositories.
2. Copy [`EFI-template/OC/ACPI/*.aml`](EFI-template/OC/ACPI/) into your `EFI/OC/ACPI/` and copy [`EFI-template/OC/config.sample.plist`](EFI-template/OC/config.sample.plist) to `EFI/OC/config.plist`.
3. Generate unique `SystemSerialNumber`, `MLB`, `SystemUUID`, and `ROM` values for `MacBookPro16,2` using `macserial` / GenSMBIOS, then validate with `ocvalidate`.
4. Follow [`docs/POST-INSTALL.md`](docs/POST-INSTALL.md) (in Chinese; see scripts & example configs in [`post-install/`](post-install/) and [`scripts/`](scripts/)) for NullMoth 2.9, `debug.nvrmfb_flip_latch=2`, and MT7922 Bluetooth firmware installation (`./scripts/install-mt7922-bt-firmware.sh`).
5. For UEFI Secure Boot coexistence with Windows 11, inspect and prepare your backed-up Preboot `boot.efi` with `./scripts/patch-apple-boot-efi-pe.py` (clears `.data` execute flag and extends `.data` `SizeOfRawData` over the 16 KB zero-padding gap so `osslsigncode` matches EDK2 `DxeImageVerificationLib` section hashing).
6. Before sharing your own EFI or fork, run `./scripts/audit-sensitive-data.sh` to catch leaked secrets or binaries.

---

## Contributors

- [@LLYSZY](https://github.com/LLYSZY) — Hardware deployment, testing, and maintenance
- Assisted by OpenAI Codex and Google Antigravity for debugging and documentation

---

## Credits & Licensing

- Upstream projects: OpenCorePkg (Acidanthera), AMD-OSX (`AMD_Vanilla`), NullMoth, YYavicWiFi, `nullarc` (`luuumi-dev`), VoodooI2C, USBToolBox, ForgedInvariant, RestrictEvents, AMDRyzenCPUPowerManagement.
- Original docs, scripts, and sanitized templates in this repository are licensed under the [MIT License](LICENSE). `patches/sequoia-timer.patch` preserves upstream MIT terms in [LICENSE.upstream](LICENSE.upstream).
