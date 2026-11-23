# Kext、驱动、内核补丁与 OpenCore 配置参考

目标环境：**OpenCore 1.0.9** · **macOS Sequoia 15.8.1 (24H32)** · 模板配置：[`../EFI-template/OC/config.sample.plist`](../EFI-template/OC/config.sample.plist)（已通过 `ocvalidate 1.0.9` 零错误校验）。

---

## 1. UEFI Drivers 与 Tools

### `EFI/OC/Drivers/`

| 文件 | 启用 | 作用 |
| --- | :---: | --- |
| `HfsPlus.efi` | ✅ | 支持读取 HFS+（含 macOS 恢复镜像与旧卷） |
| `OpenRuntime.efi` | ✅ | OpenCore 内存/NVRAM 运行时支持 |
| `ResetNvramEntry.efi` | ✅ | OpenCore 菜单中提供重置 NVRAM 入口 |
| `OpenCanopy.efi` | ✅ | 图形化启动菜单（配合 `Acidanthera\GoldenGate` 图标资源） |

### `EFI/OC/Tools/`

| 文件 | 名称 | 辅助项 (`Auxiliary`) | 说明 |
| --- | --- | :---: | --- |
| `NullMothSafe.efi` | `1401: Remove NVIDIA driver` | ✅ | 仅用于显卡驱动异常时移除 NullMoth 驱动（按空格显示辅助项） |
| `NullMothSafe.efi` | `1401: Start once without NVIDIA driver` | ✅ | 单次跳过加载 NVIDIA 驱动启动 macOS（按空格显示辅助项） |

> 安全启动提示：开启 UEFI 安全启动时，应为 `BOOTx64.efi`、`OpenCore.efi` 以及上述 4 个 `Drivers/*.efi` 签名；**不要**为具备 NVRAM 维护能力的 `NullMothSafe.efi` 或任意 UEFI Shell 签名。

---

## 2. Kexts 加载顺序与已验证版本

> 本仓库**不分发**第三方 `.kext` 二进制。请从各上游项目官方 Release 下载对应版本放入 `EFI/OC/Kexts/`，顺序与 [`config.sample.plist`](../EFI-template/OC/config.sample.plist) 保持一致：

| 顺序 | Bundle 路径 | 实测版本 | 启用 | 作用 |
| :---: | --- | --- | :---: | --- |
| 1 | `Lilu.kext` | `1.7.3` | ✅ | 驱动注入基础框架 |
| 2 | `ForgedInvariant.kext` | `1.5.0` | ✅ | AMD TSC 同步（缓解输入延迟与连击） |
| 3 | `AMFIPass.kext` | `1.4.1` | ✅ | 放行未签名/第三方系统级扩展（NullMoth 所需） |
| 4 | `AppleALC.kext` | `1.9.9` | ✅ | Realtek ALC285 声卡驱动（`layout-id=31`） |
| 5 | `AppleMCEReporterDisabler.kext` | `1.2` | ✅ | AMD 平台禁用 AppleIntelMCEReporter 防崩溃 |
| 6 | `BlueToolFixup.kext` | `2.7.3` | ✅ | 修复第三方蓝牙控制器在 macOS 12+ 的初始化 |
| 7 | `BrightnessKeys.kext` | `1.0.4` | ✅ | 笔记本屏幕亮度快捷键支持 |
| 8 | `NVMeFix.kext` | `1.1.4` | ✅ | 改善第三方 NVMe SSD 功耗与兼容性 |
| 9 | `RestrictEvents.kext` | `1.1.7` | ✅ | 配合 `revcpu`/`revcpuname`/`revpatch` 修复 CPU 名称与系统更新兼容性 |
| 10 | `VirtualSMC.kext` | `1.3.9` | ✅ | 模拟 Apple SMC |
| 11 | `SMCBatteryManager.kext` | `1.3.9` | ✅ | 电池状态与电量显示 |
| 12 | `AsusSMC.kext` | `1.4.1` | ✅ | ASUS ROG EC 风扇与温控配置支持 |
| 13 | `AMDRyzenCPUPowerManagement.kext` | `0.7.2` | ✅ | AMD Ryzen CPU 电源管理 |
| 14 | `SMCAMDProcessor.kext` | `1.0.1` | ✅ | AMD 处理器/传感器监测（兼容 Stats） |
| 15 | `SMCLightSensor.kext` | `1.3.9` | ✅ | 环境光传感器 |
| 16 | `SimpleMtkBtFw.kext` | `1.0.0` | ❌ **禁用** | 与原生方案冲突：已改用 `/etc/bluetool` 固件 + `ItlXhciKick` + `BlueToolFixup` |
| 17 | `Sinetek-rtsx.kext` | `9.0.0` | ✅ | Realtek PCIe 读卡器驱动 |
| 18 | `USBToolBox.kext` + `UTBDefault.kext` | `1.2.0` / `1.0` | ✅ | USB 端口映射与识别 |
| 19 | `VoodooI2C.kext`（含 `VoodooI2CServices` 1.0、`VoodooGPIO` 1.1、`VoodooInput` 1.1.7）+ `VoodooI2CHID.kext` | `2.9.1` / `1.0` | ✅ | I²C 精密触控板 |
| 20 | `VoodooPS2Controller.kext`（`Keyboard` / `Mouse` / `Trackpad`） | `2.3.8` | ✅ | 内置 PS/2 键盘（**其内置 `VoodooInput` 已禁用**，避免与 `VoodooI2C` 冲突） |
| 21 | `WhateverGreen.kext` | `1.7.2` | ✅ | 常规显示框架补丁 |
| 22 | `YYavicWiFi.kext` | `0.7.2` | ✅ | MediaTek MT7922 / RZ616 原生 Wi-Fi 菜单驱动 |
| 23 | `ItlXhciKick.kext` | `0.1.0` | ✅ | XHCI/蓝牙固件辅助唤醒 |

---

## 3. 关键内核与设备属性配置

### `Kernel -> Block`

- **阻止 `com.apple.iokit.IONDRVSupport`**：防止开机引导帧缓冲（`IONDRVFramebuffer`）抢占 `index 0`，确保 RTX 4060 `NVRMFB` 正常接管显示输出。

### `Kernel -> Patch`（27 项 AMD Vanilla / Sequoia 补丁）

- 基于 AMD Vanilla 17h/19h 标准补丁集（最高支持 Darwin `25.99.99`）：
  - `algrey - Force cpuid_cores_per_package`：已按 Ryzen 9 7940HS 的 **8 物理核心** (`0x08`) 配置好 `Replace` 字节；
  - 包含 Sonoma/Sequoia (`15.0+` / Darwin `24.0.0+`) 所需的 `leaf7`、`IOPCIIsHotplugPort`（AM5/Zen4 PCI 枚举）、`thread_invoke` 非单调时间补丁及 PAT 修复。

### `DeviceProperties -> Add`

| PCI 路径 | 属性 | 作用 |
| --- | --- | --- |
| `PciRoot(0x0)/Pci(0x1,0x1)/Pci(0x0,0x0)` | `acpi-wake-type = 1` | 标定外设/桥唤醒类型 |
| `PciRoot(0x0)/Pci(0x8,0x1)/Pci(0x0,0x0)` | `disable-gpu = True` | 禁用未使用的 Radeon 780M 核显路径 |
| `PciRoot(0x0)/Pci(0x8,0x1)/Pci(0x0,0x6)` | `layout-id = 31` | Realtek ALC285 声卡注入 Layout 31 |

### `NVRAM -> Add`

- **`4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102`**：
  - `revcpu = 1`、`revcpuname = AMD Ryzen 9 7940HS w/ Radeon 780M Graphics`、`revpatch = sbvmm,cpuname`
- **`7C436110-AB2A-4BBB-A880-FE41995C9F82`**：
  - `boot-args`：
    `-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=2 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0 gfxrst=4 yyavic-cc=CN`
    > 可按需将 `yyavic-cc=CN` 改为所在国家/地区两位代码（例如 `US`、`JP` 等）；日常稳定后可按需移除 `-v`。
  - `csr-active-config`：`430A0000`（允许加载未签名系统级扩展与图形驱动安装）。

### `PlatformInfo -> Generic`（SMBIOS）

- 使用 **`MacBookPro16,2`**，`CustomSMBIOSGuid = True`、`UpdateSMBIOSMode = Custom`。
- [`config.sample.plist`](../EFI-template/OC/config.sample.plist) 中的 `SystemSerialNumber`、`MLB`、`SystemUUID`、`ROM` 已替换为 OpenCore 占位符。**部署前必须用 `macserial` / GenSMBIOS 为自己生成全新且唯一的 SMBIOS。**
