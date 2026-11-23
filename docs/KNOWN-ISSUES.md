# 已知问题与待解决边界

本文件如实记录截至目前在 GA402XV + macOS Sequoia 15.8.1 (24H32) 上**尚未完全解决或未验证**的项目，避免后来者踩坑。

| 项目 | 现状与观察到的现象 | 备注 / 临时规避方式 |
| --- | --- | --- |
| **内置扬声器音质** | Realtek ALC285 (`layout-id=31`) 可发声，但声音偏细薄、有破音倾向 | 本机使用 **I²C** 连接的 Cirrus Logic CS35L41 (`1043:1463`) 功放，缺少低音单元功放初始化与板级固件配置。开源 `CirrusAudioFixup` 目前暂未收录 `1043:1463`；**切勿**套用枪神 7 的 SPI / `layout-id=21` 方案或贸然替换正常工作的 `VoodooI2C`。 |
| **USB-C 外接音箱** | 使用 Creative Pebble V3 (`041e:3272`) 在两侧 USB-C 口均出现音频提前退出与 `OutputFellBehind` | 将 CoreAudio 缓冲从 512 调大至 2048 仍无法消除；临时规避为使用内置输出，未验证 AUX 有线或蓝牙音箱对照。 |
| **Safari 与流媒体视频** | 本地 1080p60 H.264 样本已确认调用 `NVDEC` 硬解（180 帧 0 错误），本地页面 20 秒播放 1 次丢帧 | Safari 存在系统日志可见的 `blocked mmap`（上游 `safari_gpu_copy.sh` 因 SIP 保护未部署）；B 站等实际流媒体页面未在免交互限制外完成独立定量复测；AV1 / VP9 硬解受驱动限制不可用。 |
| **Radeon 780M 纯核显模式** | 已完成 macOS 15 定时器补丁与 AuxKC 链接验证 | 实机未切换 MUX 与解除 `disable-gpu`，核显桌面、RTX 4060 断电与低噪均**未验证**。 |
| **AirDrop / 接力 / 隔空播放** | MT7922 蓝牙已可正常开关工作 | AirDrop、iPhone 镜像与 Continuity 均未验证。 |
| **微 PE 与反作弊实测** | OpenCanopy 启动菜单与 UEFI `SecureBoot=1` 启动 macOS 已实测通过 | 独立微 PE 桌面及《战地 6》等游戏反作弊对签名 OpenCore 链路的最终放行未实测（需在 Windows 下按常规方式自测）。 |
| **读卡器与完整睡眠/唤醒** | 已加载 `Sinetek-rtsx.kext` 9.0.0 与 `SSDT-USBX` / `acpi-wake-type` | 长期合盖睡眠功耗与 SD 卡热插拔稳定度未做专项压测。 |
