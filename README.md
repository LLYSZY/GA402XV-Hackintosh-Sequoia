# ASUS ROG Zephyrus G14 GA402XV (2023) · macOS Sequoia

**中文** | [English](README.en.md)

面向 **2023 款华硕 ROG 幻 14 (GA402XV)** 的 macOS 黑苹果开源方案与实机维护文档。  
本仓库聚焦于**可复现、完全脱敏、严格按实机状态标注**的 OpenCore 1.0.9 配置模板、定制 ACPI 补丁、显卡高刷与安全启动工具脚本，以及 Radeon 780M 核显移植实验补丁。

> **测试基线**：macOS Sequoia **15.8.1 (Build 24H32)** · OpenCore **1.0.9** · SMBIOS **`MacBookPro16,2`**  
> **硬件平台**：AMD Ryzen 9 7940HS · NVIDIA GeForce RTX 4060 Laptop (主力图形栈) / Radeon 780M · MediaTek MT7922 (RZ616) · Realtek ALC285 + I²C CS35L41

> [!IMPORTANT]
> 本仓库**不分发** macOS 安装镜像、专有蓝牙固件二进制、第三方 `.kext`/`.efi` 编译产物、个人 SMBIOS 序列号或安全启动私钥。所有模板均已脱敏并经自动化审计脚本校验。

---

## 硬件兼容性总览（仅列本机实测状态）

| 模块 | 硬件 / 驱动栈 | 状态 | 实测说明 |
| --- | --- | :---: | --- |
| **CPU 与电源** | Ryzen 9 7940HS + AMD 27 项内核补丁 + `AMDRyzenCPUPowerManagement` + `ForgedInvariant` | ✅ 正常 | 8 核拓扑、时钟同步与 CPU 名称注入正常 |
| **独显图形与高刷** | RTX 4060 Laptop (`10DE:28E0`) + **NullMoth 2.9** | ✅ 正常 | 内屏 2560×1600 @ 165 Hz；HDMI 曾验证 4K @ 120 Hz；`debug.nvrmfb_flip_latch=2` 下 10 秒平均提交等待由 `2732 µs` 降至 `249 µs`；本地 1080p60 H.264 `NVDEC` 180 帧 0 错误 |
| **触控板与键盘** | I²C 触控板 (`VoodooI2C` 2.9.1 `-vi2c-force-polling`) + `VoodooPS2Controller` | ✅ 正常 | 关闭系统“模拟用力点按”后指针瞬移消失 |
| **Wi-Fi** | RZ616 / MT7922 (`14C3:0616`) + `YYavicWiFi 0.7.2` | ✅ 正常 | 支持原生系统 Wi-Fi 菜单连接 |
| **蓝牙** | MT7922 (`0489:E0F6`) + `BlueToolFixup` + `ItlXhciKick` + `/etc/bluetool` 固件 | ⚠️ 基础可用 | 蓝牙开关工作；AirDrop 与 Continuity 未验证 |
| **音频** | Realtek ALC285 + I²C CS35L41 (`1043:1463`, `layout-id=31`) | ⚠️ 受限 | 内置扬声器可播但声音薄/缺少低音功放初始化；USB-C 外接音箱在测试设备上有 `OutputFellBehind` 异常 |
| **UEFI 安全启动** | 保留微软证书 + 自签 OpenCore + Preboot `boot.efi` 布局修复 | ⚠️ 已启动 | 主板 `SecureBoot=1` 下已成功引导 macOS 15.8.1；系统更新后需重新签名 `boot.efi`；Windows 游戏反作弊未实测 |
| **Radeon 780M 核显** | `1002:15BF` + `nullarc` Sequoia 定时器移植补丁 | 🧪 实验阶段 | 两模块已链接进 24H32 测试内核集合且单元测试全过；主力配置仍屏蔽核显，纯核显桌面与省电静音未实测 |

---

## 仓库目录结构

```text
├── EFI-template/OC/
│   ├── config.sample.plist          # 脱敏 OpenCore 1.0.9 配置模板（ocvalidate 0 错误）
│   └── ACPI/                        # 本机全部 6 个已编译 SSDT (.aml)
├── acpi/
│   ├── SSDT-ALIB-Return.dsl         # 修复 GA402XV A026/ALIB 缺返回值问题的源码
│   └── README.md                    # SSDT 用途与 ACPI 重命名详解
├── docs/
│   ├── HARDWARE-AND-BIOS.md         # 硬件规格、机型差异避坑与 BIOS 设置清单
│   ├── KEXTS-AND-DRIVERS.md         # 全量 Kext 版本表、内核补丁与设备属性说明
│   ├── POST-INSTALL.md              # 显卡驱动、165Hz latch、Wi-Fi/蓝牙固件与触控板调优
│   ├── SECURE-BOOT.md               # 双系统保留微软证书的 UEFI 安全启动完整签名方案
│   ├── IGPU-780M-EXPERIMENT.md      # 780M macOS 15 定时器补丁重现实验与边界
│   └── KNOWN-ISSUES.md              # 已确认局限与待解决事项清单
├── patches/
│   └── sequoia-timer.patch          # nullarc PhxBringup 移植到 macOS 15 的定时器补丁
├── post-install/
│   ├── local.ga402xv.display-submit.plist  # 持久化 debug.nvrmfb_flip_latch=2 开机项
│   └── nvrm610.conf.example         # NullMoth 2.9 推荐配置文件示例
└── scripts/
    ├── check-gpu.sh                 # 只读检查双卡 PCI 枚举与 flip_latch 状态
    ├── install-mt7922-bt-firmware.sh # 校验 SHA-256 并安全安装 MT7922 蓝牙固件
    ├── patch-apple-boot-efi-pe.py   # 修复 Apple boot.efi W^X 与 .data 零空隙以通过 UEFI 验签
    └── audit-sensitive-data.sh      # 提交/打包前敏感数据与违规文件自动审计脚本
```

---

## 快速上手（组装你自己的 EFI）

1. **下载基础引导与驱动**：准备 **OpenCore 1.0.9**（含 `OpenCore.efi`、`BOOTx64.efi`、`HfsPlus.efi`、`OpenRuntime.efi`、`ResetNvramEntry.efi`、`OpenCanopy.efi` 及 `Resources/`），并按 [`docs/KEXTS-AND-DRIVERS.md`](docs/KEXTS-AND-DRIVERS.md) 从上游仓库收集对应版本的 Kext。
2. **复制配置与 ACPI**：将 `EFI-template/OC/ACPI/*.aml` 放入你的 `EFI/OC/ACPI/`，将 `EFI-template/OC/config.sample.plist` 复制为 `EFI/OC/config.plist`。
3. **生成唯一 SMBIOS**：使用 `macserial` / GenSMBIOS 为 `MacBookPro16,2` 生成全新的 `SystemSerialNumber`、`MLB`、`SystemUUID` 与 `ROM`，替换 `config.plist` 中 `PlatformInfo -> Generic` 的占位符，并用 `ocvalidate` 检查。
4. **按需完成安装后配置**：依照 [`docs/POST-INSTALL.md`](docs/POST-INSTALL.md) 部署 NullMoth 2.9、高刷提交参数、MT7922 蓝牙固件与触控板设置。
5. **需要开启主板安全启动时**：参考 [`docs/SECURE-BOOT.md`](docs/SECURE-BOOT.md) 签名 OpenCore，并使用 `scripts/patch-apple-boot-efi-pe.py` 预处理 Apple Preboot `boot.efi`。

---

## 贡献者

- [@LLYSZY](https://github.com/LLYSZY)：实机部署、测试验证与仓库维护
- 协助整理与调试记录：OpenAI Codex、Google Antigravity

---

## 鸣谢与许可

- 感谢上游开源社区与开发者：[Acidanthera / OpenCorePkg](https://github.com/acidanthera/OpenCorePkg)、[AMD-OSX / AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla)、[NullMoth](https://github.com/nullmoth)、[YYavicWiFi](https://github.com/yusufcanyavic/YYavicWiFi)、[nullarc (luuumi-dev)](https://github.com/luuumi-dev/nullarc)、[VoodooI2C](https://github.com/VoodooI2C/VoodooI2C)、[USBToolBox](https://github.com/USBToolBox/tool)、[ForgedInvariant](https://github.com/ChefKissInc/ForgedInvariant)、[RestrictEvents](https://github.com/acidanthera/RestrictEvents)、[AMDRyzenCPUPowerManagement](https://github.com/trulyspinach/SMCAMDProcessor)。
- 本仓库原创文档、配置模板与脚本采用 [MIT License](LICENSE)；`patches/sequoia-timer.patch` 保留上游 `nullarc` 的 MIT 版权声明，见 [LICENSE.upstream](LICENSE.upstream)。
