# 硬件规格与 BIOS 设置指南

## 目标机型：ASUS ROG Zephyrus G14 (2023) — GA402XV

| 子系统 | 硬件组件 / 公开 PCI/USB 标识 | macOS Sequoia 15.8.1 (24H32) 现状 |
| --- | --- | --- |
| **处理器** | AMD Ryzen 9 7940HS (Zen 4 / Phoenix, 8C/16T) | ✅ 正常工作（OpenCore AMD 27 项内核补丁 + `AMDRyzenCPUPowerManagement` + `ForgedInvariant`） |
| **独立显卡 (主力)** | NVIDIA GeForce RTX 4060 Laptop (`10DE:28E0`, 8 GB / 8192 MiB BAR1) | ✅ NullMoth 2.9 驱动：内屏 2560×1600 @ 165 Hz；HDMI 外接曾验证 4K @ 120 Hz；H.264 NVDEC 样本验证通过 |
| **核芯显卡** | AMD Radeon 780M (`1002:15BF`) | ⚠️ 当前主力配置通过 `disable-gpu` 禁用；macOS 15 核显链接补丁详见 [780M 实验文档](IGPU-780M-EXPERIMENT.md) |
| **内存** | DDR5-4800（板载 16 GB + 1× SO-DIMM 插槽，支持扩展至 32 GB+） | ✅ 16 GB / 32 GB 实机均正常 |
| **固态硬盘** | PCIe 4.0 NVMe SSD（实测含 XPG GAMMIX S30 2 TB） | ✅ 正常工作（`NVMeFix.kext`） |
| **无线网卡** | MediaTek MT7922 / AMD RZ616 (`14C3:0616`) | ✅ `YYavicWiFi 0.7.2` 原生菜单接入（参见 [安装后指南](POST-INSTALL.md)） |
| **蓝牙** | MediaTek MT7922 / RZ616 (`0489:E0F6`) | ✅ `BlueToolFixup` + `ItlXhciKick` + `/etc/bluetool` 固件后可开关与连接（AirDrop 未验证） |
| **声卡与功放** | Realtek ALC285 + I²C Cirrus Logic CS35L41 (`1043:1463`, `layout-id=31`) | ⚠️ 内置扬声器可播但声音偏薄；USB-C 音箱存在等时传输异常（详见 [已知问题](KNOWN-ISSUES.md)） |
| **触控板 / 键盘** | I²C 精密触控板 + PS/2 内建键盘 | ✅ `VoodooI2C` (`-vi2c-force-polling`) + `VoodooPS2Controller`；关闭模拟用力点按后瞬移消失 |
| **读卡器** | Realtek PCIe SD 读卡器 | ✅ 已配置 `Sinetek-rtsx.kext` 9.0.0（待按需实测） |

---

## ⚠️ 重要兼容性边界（请勿盲套其它机型方案）

1. **勿用 2020–2022 款 G14 EFI**：
   - 2020/2021 款为 Ryzen 4000/5000 + Vega 核显（NootedRed 路线）；
   - 2022 款（GA402RJ/RK）为 RX 6700S/6800S 独显；
   - 2023 款 **GA402XV** 为 Zen 4 (7940HS) + **RTX 4060**，显卡、ACPI (`A026`)、音频总线完全不同，不可混用。
2. **勿套用 Intel 平台（如枪神 7 / i9-13980HX）的一键脚本或音频/电源配置**：
   - 本机为 AMD 平台，**不可使用** `CPUFriend` / `CCToolBox` 或 Intel 电源向量；
   - 本机功放走 **I²C**，**不是** Intel ROG 常见的 SPI CS35L41 / `layout-id=21`。请勿为调音质贸然替换正在工作的 `VoodooI2C.kext`，否则触控板可能失效。
3. **显示路由说明**：
   - 在独显模式（dGPU / Ultimate）下，Windows 与 macOS 实测内屏 eDP 与 HDMI 均连接至 RTX 4060，Radeon 780M 在固件/设备树中不枚举。

---

## BIOS 设置检查清单

进入 BIOS（开机按 **F2**，**F7** 切换高级模式）：

- **Fast Boot**：建议设为 `Disabled`（便于读取启动热键与 USB 初始化）。
- **GPU 模式（MUX Switch）**：主力 macOS 使用 **dGPU / Ultimate** 模式，由 RTX 4060 接管内屏和 HDMI；若要研究 Radeon 780M，需改回 Hybrid/MSHybrid 并使用独立测试 U 盘。
- **Resizable BAR**：Windows 端在独显模式实测 BAR1 为 8192 MiB（部分工具报告字段可能与实际不一致，不要盲目魔改 BIOS 选项）；OpenCore 配置中保持 `Booter -> Quirks -> ResizeAppleGpuBars = 0`、`UEFI -> Quirks -> ResizeGpuBars = -1`。
- **Secure Boot（UEFI 安全启动）**：
  - 安装调试初期可暂设 `Secure Boot Control = Disabled`；
  - 需要与 Windows 11 反作弊软件长期共存时，可按 [UEFI 安全启动指南](SECURE-BOOT.md) 给 OpenCore 及 macOS Preboot `boot.efi` 签名，再在 `Key Management -> Authorized Signatures (db)` 中**追加**公钥证书；
  - **切勿随意清除 PK/KEK/db 或恢复 Setup Mode**，以免影响微软启动信任链或 BitLocker。
