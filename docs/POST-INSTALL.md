# 安装后配置与性能调优指南

本指南整理了在 **macOS Sequoia 15.8.1 (24H32)** 上完成基础系统安装后，让 GA402XV 达到当前最佳可用状态的全部步骤。

---

## 1. 生成个人 SMBIOS（必须执行）

复制 [`../EFI-template/OC/config.sample.plist`](../EFI-template/OC/config.sample.plist) 为 `EFI/OC/config.plist`，并使用 OpenCore 官方 `macserial`（或 GenSMBIOS）为 `MacBookPro16,2` 生成专属于你的四项标识并填入 `PlatformInfo -> Generic`：

- `SystemSerialNumber`
- `MLB`
- `SystemUUID`
- `ROM`（可使用本机真实或随机生成的 6 字节 MAC 地址）

---

## 2. 安装 RTX 4060 图形驱动（NullMoth 2.9）

1. 按 NullMoth 官方说明安装 **NullMoth 2.9**（包含 `NVRM`、`NVRMFB`、`NVRMAGDC`、`NVAccel` 四个内核模块及用户态 `NVMTLDriver.bundle`）。
2. 参考 [`../post-install/nvrm610.conf.example`](../post-install/nvrm610.conf.example) 检查 `/Library/GPUBundles/nvmtl/nvrm610.conf`：
   - 本机保留 `NVMTL_NO_NVENC=1` 与 `NVMTL_NO_NVENC_HEVC=1`；
   - 不建议长期保留 `BOOST=0` 或 `NVMTL_NO_NVDEC=1`（实测 2.9 驱动的 `NVDEC` H.264 样本解码可 0 错误完成 180 帧）。
3. 重启后确认四个模块版本均为 `2.9`：
   ```sh
   kmutil inspect --show-extension-info | grep -E 'NVRM|NVAccel'
   ```
4. 运行只读诊断确认设备可见性：
   ```sh
   ./scripts/check-gpu.sh
   ```

---

## 3. 高刷桌面呈现优化（`debug.nvrmfb_flip_latch=2`）

在 GA402XV 内屏 2560×1600 @ 165 Hz（及外接 4K @ 120 Hz）下，默认 `debug.nvrmfb_flip_latch=1` 的帧等待时间较高。实测开启 `2` 后（10 秒动画对照测试）：
- `latch = 1`：478 次提交，平均等待 **2732 µs**
- `latch = 2`：1284 次提交，平均等待 **249 µs**（0 超时、0 异常丢弃）

### 安装持久化开机项

```sh
sudo cp post-install/local.ga402xv.display-submit.plist /Library/LaunchDaemons/
sudo chown root:wheel /Library/LaunchDaemons/local.ga402xv.display-submit.plist
sudo chmod 644 /Library/LaunchDaemons/local.ga402xv.display-submit.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/local.ga402xv.display-submit.plist
```

> **提示**：由于 `RunAtLoad` 可能在第三方显卡驱动加载完成前触发，重启后建议用 `./scripts/check-gpu.sh` 核实 `debug.nvrmfb_flip_latch` 是否确认为 `2`；若仍为 `1`，可手动执行 `sudo sysctl -w debug.nvrmfb_flip_latch=2`（或 `sudo launchctl kickstart -k system/local.ga402xv.display-submit`）。

### 如出现闪烁/异常的回退方法

```sh
sudo launchctl bootout system/local.ga402xv.display-submit
sudo rm /Library/LaunchDaemons/local.ga402xv.display-submit.plist
sudo sysctl -w debug.nvrmfb_flip_latch=1
```

---

## 4. RZ616 / MT7922 无线网卡与蓝牙配置

1. **Wi-Fi**：`EFI/OC/Kexts/` 中启用 `YYavicWiFi.kext` (0.7.2)，在 `boot-args` 中设置地区码 `yyavic-cc=CN`（按实际地区调整），重启后直接使用 macOS 系统原生 Wi-Fi 菜单连接。
2. **蓝牙**：
   - `config.sample.plist` 已启用 `BlueToolFixup.kext` + `ItlXhciKick.kext`，并**禁用**冲突的 `SimpleMtkBtFw.kext`。
   - 从上游 `linux-firmware`（`mediatek/BT_RAM_CODE_MT7922_1_1_hdr.bin`）获取固件文件后，执行：
     ```sh
     sudo ./scripts/install-mt7922-bt-firmware.sh /path/to/BT_RAM_CODE_MT7922_1_1_hdr.bin
     ```
   - 该脚本会先校验固件 SHA-256（`299942dbec7d34af030670ea59f9f7b4fd5c64e738b9e0157d76f4dd3beb190f`），若已存在旧固件则先备份，再以 `644` 权限原子安装到 `/etc/bluetool/BT_RAM_CODE_MT7922_1_1_hdr.bin`。安装后**重启 macOS** 即可正常开关蓝牙。

---

## 5. 触控板光标瞬移修复

如果遇到指针偶发跳变/瞬移，请在 macOS **系统设置 → 触控板 → 点按** 中**关闭“用力点按和触感反馈”**（Force Touch 模拟）。本机实测关闭后指针瞬移问题立即消失。

---

## 6. 图形多系统启动菜单（OpenCanopy）

模板 `config.sample.plist` 已按统一菜单方案配置：
- `Misc -> Boot -> PickerMode = External`
- `PickerVariant = Acidanthera\GoldenGate`（需将 OpenCore 官方 `Resources/` 放入 `EFI/OC/Resources/`）
- `Timeout = 0`（菜单无限等待，直到手动回车选择），`HideAuxiliary = True`（按空格键可显示 `NullMothSafe` 与 `ResetNvram` 等辅助项）
- `LauncherOption = Full`（向主板固件登记稳定的 OpenCore 启动项）

双系统维护建议：
- 保留 Windows ESP 原生 `EFI/Microsoft/Boot/bootmgfw.efi`，并将 Windows BCD 的 `timeout` 设为 `0`，避免从 OpenCore 选 Windows 后再等待第二层菜单。
- 各分区可用 `.contentDetails` 自定义在 OpenCanopy 中显示的系统名称（如 `Windows 11`）。
