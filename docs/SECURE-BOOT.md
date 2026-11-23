# UEFI 安全启动（Secure Boot）双系统签名指南

本指南记录如何在 **不删除微软原厂证书、不关闭游戏所需的固件 UEFI Secure Boot** 的前提下，通过 OpenCore 启动 macOS Sequoia 与 Windows 11。

---

## 1. 先分清两个“安全启动”

| 概念 | 所在层级 | 本机要求状态 | 说明 |
| --- | --- | :---: | --- |
| **UEFI Secure Boot** | 主板固件（PK / KEK / db / dbx） | **开启 (`SecureBoot=1`)** | 校验引导阶段的 `.efi` PE 签名，Windows 11 反作弊游戏通常强制要求开启 |
| **Apple Secure Boot** | OpenCore (`SecureBootModel`) | **`Disabled`**（`Vault=Optional`） | 与 AMD 内核补丁及第三方 NullMoth 显卡驱动冲突，必须保持关闭 |

---

## 2. 安全原则（操作前必读）

- **保留固件原有证书链**：保留主板自带的 `PK`、`KEK`、`db`（包含微软 2011 与 2023 UEFI CA 证书）和 `dbx`。
- **仅向 `db`（Authorized Signatures）追加你的自定义证书**：不要“清除密钥 / Restore Factory Keys / 切换到 Setup Mode 后覆盖 db”，以免破坏 Windows 引导或 BitLocker 恢复链。
- **私钥本地保存，绝不进入 EFI 或公开仓库**：
  - 私钥（`.key`）设权限 `chmod 600` 放在本机受限目录；
  - 只有**公钥证书**（`.cer` 或 `.esl`）复制到 BIOS 可读取的 FAT 分区用于登记。
- **不要签名高危维护工具**：`NullMothSafe.efi` 或任何 UEFI Shell 拥有高权限 NVRAM/磁盘操作能力，请勿对其签名；需要用时可暂时关闭 Secure Boot 进入维护。

---

## 3. 生成证书并签名 OpenCore 引导文件

### 3.1 生成本地 RSA-2048 / SHA-256 代码签名证书

```sh
mkdir -p private && chmod 700 private
openssl req -newkey rsa:2048 -nodes -keyout private/OpenCore-db.key \
  -new -x509 -sha256 -days 3650 -subj "/CN=GA402XV OpenCore db/" \
  -out private/OpenCore-db.pem
openssl x509 -in private/OpenCore-db.pem -outform DER -out OpenCore-db.cer
chmod 600 private/OpenCore-db.key
```

> 若固件菜单要求 UEFI Signature List 格式，可使用 `efitools` 中的 `cert-to-efi-sig-list` 从 `.pem` 转换生成 `.esl`。

### 3.2 签名 6 个 OpenCore EFI 文件

使用 `osslsigncode`（实测版本 `2.14`）为已备份并校验正常的以下 6 个文件签名：
- `EFI/BOOT/BOOTx64.efi`
- `EFI/OC/OpenCore.efi`
- `EFI/OC/Drivers/HfsPlus.efi`
- `EFI/OC/Drivers/OpenRuntime.efi`
- `EFI/OC/Drivers/ResetNvramEntry.efi`
- `EFI/OC/Drivers/OpenCanopy.efi`

示例命令：
```sh
osslsigncode sign \
  -certs private/OpenCore-db.pem \
  -key private/OpenCore-db.key \
  -h sha256 \
  -n "GA402XV OpenCore" \
  -in input.efi -out signed.efi
```

### 3.3 在华硕 BIOS 中追加信任

1. 将公钥 `OpenCore-db.cer`（及 `.esl`）放入 FAT32 格式 ESP（例如 `EFI/SecureBoot/`）。
2. 进入 BIOS → **Security → Secure Boot → Key Management**。
3. 选择 **Authorized Signatures (`db`) → Append（追加）** → 从文件加载 `OpenCore-db.cer`。
4. 确认原微软证书仍在，再启用 **Secure Boot Control = Enabled** 并保存。

---

## 4. 修复 macOS `OCB: LoadImage failed - Access Denied`

在 BIOS 成功注册证书后，OpenCore 菜单可正常显示，但选择启动 macOS 时仍可能遇到 `OCB: LoadImage failed - Access Denied`。本机定位并验证了**三个根因**，仓库自带工具 [`../scripts/patch-apple-boot-efi-pe.py`](../scripts/patch-apple-boot-efi-pe.py) 已整合前两项预处理：

### 根因 A：`FixupAppleEfiImages = True` 在内存中修改 `.data` 权限
- OpenCore 会把 Apple `boot.efi` 的 `.data` 节从可写可执行（`0xe0000060`）修正为不可执行（`0xc0000060`，W^X），导致**签名前后文件哈希与内存加载校验不符**。
- **解决**：签名前先用本仓库脚本清除 `.data` 的 `IMAGE_SCN_MEM_EXECUTE`（`0x20000000`）标志位。

### 根因 B：`osslsigncode` 线性哈希与 EDK2 分节哈希差异（16 KB 零填充空隙）
- macOS Sequoia 15.8.1 (24H32) 的 Preboot `boot.efi` 中，`.data` 节 `SizeOfRawData`（`12288`）小于 `VirtualSize`（`28672`），与 `.reloc` 之间存在 **16384 字节全零空隙**。
- `osslsigncode` 按整文件线性计算 Authenticode 摘要，而主板固件（EDK2 `DxeImageVerificationLib`）按 PE 头 + 排序后的各节 `SizeOfRawData` + 尾部字节计算摘要，导致两者摘要不一致而被固件拒载。
- **解决**：[`patch-apple-boot-efi-pe.py`](../scripts/patch-apple-boot-efi-pe.py) 会逐字节确认该空隙全为 `0x00`（非零则拒绝操作），然后将 `.data` 的 `SizeOfRawData` 扩展至 `VirtualSize`（不改变文件长度与任何节的偏移），并独立对比线性摘要与 EDK2 摘要完全一致。

### 根因 C：Preboot `bless` inode 失配
- 如果采用 `mv` 等原子替换方式更新 Preboot 卷中的 `boot.efi`，文件的 inode 会改变，导致 APFS Preboot 的 `Blessed System File` 仍指向旧 inode 或失效。
- **解决**：备份原 `boot.efi` 后，**原位写回**已签名内容保持 inode 不变，或使用 `bless --folder ... --file ...`（不要加 `--setBoot`）同步恢复记录。

### 使用示例

```sh
# 1. 只读检查（请先复制一份 Preboot boot.efi 备份再操作）
./scripts/patch-apple-boot-efi-pe.py --inspect boot-original.efi

# 2. 预处理 W^X 与 .data 零空隙（输出为新文件，绝不直接覆盖原件）
./scripts/patch-apple-boot-efi-pe.py --patch boot-original.efi --output boot-patched.efi

# 3. 使用你的证书签名
osslsigncode sign \
  -certs private/OpenCore-db.pem \
  -key private/OpenCore-db.key \
  -h sha256 \
  -n "macOS Preboot Loader" \
  -in boot-patched.efi -out boot-signed.efi
```

---

## 5. 维护注意与验证边界

- **macOS 系统更新会替换 Preboot `boot.efi`**：更新系统前建议暂关 BIOS 安全启动，更新完成后对新的 `boot.efi` 重新备份、运行 `patch-apple-boot-efi-pe.py`、签名并核对 `bless --info`。
- **实测边界**：本机已验证固件 `SecureBoot=%01` 下可经由 OpenCore 顺利进入 macOS 15.8.1；Windows 反作弊游戏（如《战地 6》）在签名 OpenCore 链路下的在线反作弊校验尚未实测，若游戏拦截，可重启通过固件原生 `Windows Boot Manager` 作为干净对照路径。
