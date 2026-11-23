# ACPI 配置说明 (GA402XV)

本目录收录适用于 **ASUS ROG Zephyrus G14 GA402XV (2023, Ryzen 9 7940HS)** 的定制 SSDT 源码与说明；编译后的 `.aml` 文件位于 [`../EFI-template/OC/ACPI/`](../EFI-template/OC/ACPI/)。

## SSDT 清单

| 文件 | 用途 | 备注 |
| --- | --- | --- |
| `SSDT-ALIB-Return.aml` | 修复本机 ACPI `ALIB` / `A026` 方法缺少返回值的问题 | 本仓库提供源码 [`SSDT-ALIB-Return.dsl`](SSDT-ALIB-Return.dsl)，必须配合 `ACPI -> Patch` 中的 `A026 -> X026` 重命名使用。 |
| `SSDT-EC.aml` | 注入虚拟 Embedded Controller (`EC`) 设备 | AMD 黑苹果必需，满足 macOS `AppleBusPowerController` 与电源管理加载。 |
| `SSDT-PLUG-ALT.aml` | 为处理器核对象注入 `plugin-type = 1` | 现代 AMD / x86_64 通用格式 (`ACPI0007`)。 |
| `SSDT-USB-Reset.aml` | 在 `Darwin` 下重置并重新枚举内置 XHCI USB 控制器端口 | 配合 `USBToolBox` 端口映射使用（涵盖 `GP17.XHC0`/`XHC1`、`GP19.XHC2`/`XHC3`/`XHC4`）。 |
| `SSDT-USBX.aml` | 注入 `USBX` 电源属性 | 提供睡眠/唤醒端口供电限制参数（`kUSBSleepPortCurrentLimit` / `kUSBWakePortCurrentLimit`）。 |
| `SSDT-XOSI.aml` | 模拟 Windows `_OSI` 响应 | 必须配合 `ACPI -> Patch` 中的 `_OSI -> XOSI` 重命名使用。 |

## 本机关键修复：`SSDT-ALIB-Return`

GA402XV 固件中的 `\_SB.A026`（ALIB 相关方法）在特定调用路径下未提供 `Return` 返回值。在安装或引导阶段，这会触发 macOS ACPI 解释器异常。

本仓库采用**安全包裹重命名**方式（不丢弃原厂逻辑）：
1. 在 `config.sample.plist` 的 `ACPI -> Patch` 中仅重命名 `A026` 的方法定义字节序列：
   - `Find`: `1410413032360170684144303041303131`
   - `Replace`: `1410583032360170684144303041303131`（将定义名 `A026` 改为 `X026`，避免误改其它调用点）。
2. 加载 [`SSDT-ALIB-Return.dsl`](SSDT-ALIB-Return.dsl) 编译出的 `SSDT-ALIB-Return.aml`：
   ```asl
   External (\_SB.X026, MethodObj)
   Scope (\_SB)
   {
       Method (A026, 1, NotSerialized)
       {
           X026 (Arg0)
           Return (Zero)
       }
   }
   ```
   这样既保留原厂 `X026(Arg0)` 的全部硬件动作，又确保向调用方返回 `Zero`。
