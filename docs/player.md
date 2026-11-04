# Jellyfin 桌面端 → PotPlayer

## 当前实现（2026-11-05）

由 JavaScript Injector 加载限定本机桌面 DeviceId、要求登录的 PlayBridge 适配脚本。点击播放后，向 `http://127.0.0.1:18097/play` 发送带本机令牌的 JSON，由 `potplayer_local_server.py` 调用 PotPlayer，读取 `X:\动漫`。

上游：[PlayBridge](https://github.com/Damocles-fr/PlayBridge)、[JavaScript Injector](https://github.com/n00bcodr/Jellyfin-JavaScript-Injector)。遵循各自许可证；最终绑定个人设备和令牌的配置不在仓库中。

## 本轮修复

旧适配通过 `NativeShell.openUrl` 打开 `playbridge:///X%3A/...`。普通桌面环境中 Windows 找不到协议应用，Jellyfin 有日志，URI 处理器没有收到调用。现在使用本机 HTTP，`register_potplayer_bridge.py` 保留为历史实现。

首次 HTTP 版本要求固定 Origin；实测 JMP 原生网络层省略此头，导致正确令牌也被拒绝。现在接受预期网页来源或没有 Origin 的原生请求，两种情况都要求随机生成的每台机器专属令牌。其他网页来源、错误令牌、空令牌均拒绝。

旧桥接和新桥接还曾同时绑定同一端口，导致请求落在旧代码。服务改为独占绑定；升级先关闭旧桥接，再启动当前版本。不能仅凭 `/health` 有响应就宣称新源码生效。

## 本机部署

```text
<运行根目录>\player\
├─ PotPlayer\PotPlayerMini64.exe
└─ bridge\
   ├─ potplayer_bridge.py
   ├─ potplayer_local_server.py
   └─ local-server.json   # 私密，仅留本机
```

配置中的 `token` 由部署者随机生成，与本机注入脚本 Bearer 令牌一致。可选 `runtime_root` 指定运行根目录；默认由处理器位置推导。不要提交真实配置或把令牌贴进公共问题报告。

服务仅监听 IPv4 回环地址。`GET /health` 只读，`POST /play` 负载只有 `uri` 字段；媒体必须存在于 `X:\动漫`，拒绝库外路径、父目录跳转、额外查询与非视频文件。参数数组调用固定播放器，不启动 shell。

本机观影入口按需启动桥接，另有当前用户登录后的 `pythonw.exe` 静默入口。使用绝对路径，注意 MSIX 和普通进程的 LocalAppData 视图差异。二进制、快捷方式和完整安装器不随源码归档发布。

## 注入适配要点

保留上游设备限制与登录要求，将 `openLink` 改成带令牌的 POST。仅替换明确的配置常量，不对整个脚本全文替换占位词。剧集和季如果 `IsFolder` 为真，要先解析可播放子项，不能直接传目录给播放器。

以下仅是函数内部说明片段，`uri` 由上游路径函数产生，不能单独当完整注入脚本使用：

```javascript
fetch('http://127.0.0.1:18097/play', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: 'Bearer YOUR_LOCALLY_GENERATED_TOKEN'
  },
  body: JSON.stringify({ uri })
});
```

## 实测与解码器

2026-11-05 从 Jellyfin 实际点击《幽灵公主》和《无职转生》S01E12，核对启动日志、正确 X 盘文件、画面和推进的计时。电影已观察到中文字幕。早期《白箱》《轻音少女 剧场版》的记录属于历史验收，本轮以重新点击的结果为准。

《幽灵公主》最初成功唤起但 DTS-HD 解码失败，提示中包含泛化的 DirectX/音频设备说明。核对后从 Kakao 官方 CDN 获取签名有效的 OpenCodec，解压并只补齐播放器本地模块，随后画面和计时正常，状态栏显示 DTS-HD。媒体未重新下载，也未安装系统级解码包。

本轮模块位置为 `Module/FFmpeg63`、`Module/OpenCodec` 及 `Module/libmfxsw64.dll`，具体目录应以匹配版本的官方包为准。DLL 和安装包不在公共仓库中。

## 排查和回退

1. 确认 CloudDrive2、X 盘可读，Jellyfin 连接正确本机服务。
2. 检查 `/health` 和端口所属进程，排除旧桥接残留。
3. `Unauthorized` 应核对令牌与 Origin 处理，不直接删除校验。
4. 已有 `local PotPlayer started` 则继续看播放器实际错误、音轨解码、文件读取。
5. 用本机观影入口恢复桥接；客户端清空数据后核对 DeviceId。

回退内置播放：在 Jellyfin 的 JavaScript Injector 插件中关闭 `AnimeLibrary PotPlayer Desktop`，保存并重开桌面客户端。

**PotPlayer 进度和已看状态不自动回传 Jellyfin。** Jellyfin 字幕/音轨选项不随此路径传递，应在 PotPlayer 内切换。18097 端口不应暴露给朋友或互联网。
