# Radeon 780M (1002:15BF) Sequoia 纯核显适配实验记录

本文档记录在 GA402XV 上基于上游开源项目 [nullarc](https://github.com/luuumi-dev/nullarc/tree/8aba872560a3c9b7dc7a0ddebfad001c6dddf315)（v0.4.0-alpha 阶段）移植 macOS Sequoia 15.8.1 (24H32) 核显驱动的研发实验与当前边界。

> **结论摘要**：`PhxBringup.kext` 与 `PhxAccel.kext` 已成功针对 macOS 15.8.1 编译并链接进测试辅助内核集合（AuxKC），`nmplugin` 也已用 macOS 15 SDK 重新编译。但本机当前 OpenCore 配置禁用了核显且处于独显显示路由模式下，**尚未完成实机纯核显点亮、RTX 4060 断电与低噪验证**。

---

## 1. 原版 nullarc 为何无法直接用于 macOS 15.8.1

原版 `nullarc` 安装目标指向 **macOS 26 (Tahoe, Kernel 25.0.0+)**，直接在本机 Sequoia `24H32` 上存在四处阻塞：
1. `PhxBringup.cpp` 调用了 `thread_call_cancel_wait`，该符号在 macOS 15.8.1 (`24H32`) 内核中未导出，导致 `kmutil create` 链接失败：
   `Failed to bind '_thread_call_cancel_wait' in 'org.drip.PhxBringup'`。
2. `PhxAccel` 默认开启 `-DNM_TAHOE`，引用了 macOS 26 专用加速接口层。
3. 用户态 Metal 插件 `nmplugin` 预编译版本链接目标高于 macOS 15。
4. 原版安装器会替换同名的 `NVMTLDriver.bundle`，直接覆盖会破坏当前正在工作的 NullMoth RTX 4060 图形栈。

---

## 2. 本仓库提供的移植补丁与重现步骤

基于上游 commit `8aba872560a3c9b7dc7a0ddebfad001c6dddf315`：

1. **检查本机 GPU 设备树可见性**（只读）：
   ```sh
   ./scripts/check-gpu.sh
   ```
   若输出 `pci1002,15bf: not enumerated`，说明固件当前未暴露 780M（或被 OpenCore `disable-gpu` 屏蔽），只能先做离线编译与链接验证。

2. **应用 Sequoia 定时器移植补丁**：
   ```sh
   git apply /path/to/patches/sequoia-timer.patch
   ```
   [`../patches/sequoia-timer.patch`](../patches/sequoia-timer.patch) 将 `PhxBringup.cpp` 中依赖 `thread_call_cancel_wait` 的 500 ms 挂起检测定时器，重构为标准 IOKit `IOWorkLoop` + `IOTimerEventSource`，并在 `stop()` 中通过 `disable()` / `cancelTimeout()` / `removeEventSource()` 安全同步销毁。

3. **构建三个组件**：
   - **PhxBringup.kext**：应用补丁后使用原项目 `src/phxbringup/build.sh` 与 `MacKernelSDK` 编译。
   - **PhxAccel.kext**：编译参数中移除 `-DNM_TAHOE`。
   - **nmplugin (`NVMTLDriver.bundle`)**：使用 macOS 15.5 SDK、`Vulkan-Headers` v1.4.335 及 `MACOSX_DEPLOYMENT_TARGET=15.0` 编译。

4. **AuxKC 内核集合离线链接验证**：
   实测使用 `kmutil create -n aux ... -p PhxAccel.kext -p PhxBringup.kext -A validated-test.kc -z` 与 `kmutil inspect -A validated-test.kc --show-extension-info` 验证通过：
   - `org.drip.PhxBringup` (`1.0.0`) 与 `com.luuumi.PhxAccel` (`0.1`) 均成功解析符号并链接；
   - 上游 RDNA3 单元测试（IP Discovery & UMA ReBAR、IP Blocks & DCN 3.1.4 Scanout、UCODE 提取、R3N ABI / RADV Winsys、Phoenix 拓扑、`doWaitSeq`）全部通过。

---

## 3. 后续继续实机验证的注意事项

如果你希望接力测试“纯核显低功耗”路线，请务必遵守以下安全边界：
1. **不要改动主硬盘正常引导**：使用独立 U 盘中的测试 EFI，并准备独立的 APFS 测试卷安装，避免覆盖主力系统正在使用的 `NVMTLDriver.bundle`。
2. **先核对硬件路由**：不仅要在 OpenCore 中移除 `PciRoot(0x0)/Pci(0x8,0x1)/Pci(0x0,0x0)` 上的 `disable-gpu`，还需将 BIOS / 华硕 MUX 切回 Hybrid/MSHybrid，确认内屏 eDP 与 `1002:15BF` 在 macOS 设备树中被实际枚举。
3. **关注功能局限**：上游 `nullarc` 当前阶段未实现硬件视频解码、HDMI/USB-C 外接输出与完整睡眠，且无硬解时播放高码率视频仍可能增加 CPU 负载与风扇噪声，因此**需实机验证后才能决定是否适合日用**。
