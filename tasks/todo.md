# 苏宁小 biu 智家短信登录接入任务

## Plan

- [x] 分析 HAR 中与手机验证码登录、SSO 跳转、Cookie 下发相关的关键请求与响应
- [x] 初始化 `uv` Python 项目，补充依赖与基础目录结构
- [x] 实现短信验证码发送、验证码登录、Cookie 持久化与恢复
- [x] 实现最小可用的会话校验与保活请求
- [x] 编写验证脚本或测试，证明登录后能访问智能家居相关接口
- [x] 分析 `clientservices.googleapis.com_2026_03_20_00_33_46.har`，确认 IAR 桥接链路是否存在异常
- [x] 实测 `.suning-session.json` 的跨进程恢复行为，区分“会话失效”和“接口签名缺失”
- [x] 从 HAR 提取可复用的 App 端已签名请求模板，补齐 `families` / `devices` 的 MVP 读取链路
- [x] 补充测试与文档，验证 `check` / `families` / `devices` 的当前可用边界
- [x] 回填实现结果、风险与后续工作

## Notes

- 当前输入包含 `apm.suning.cn_2026_03_19_23_47_23.har` 与 `clientservices.googleapis.com_2026_03_20_00_33_46.har`
- Python 相关操作统一使用 `uv`
- 目标先做可复用的登录客户端，不直接耦合 Home Assistant 平台代码
- 当前优先级是“先把 MVP 功能做出来”，暂不继续打磨验证码桥接页 UI

## Review

- 已实现 `src/suning_biu_ha/crypto.py`
  - 复刻苏宁 `SuAES` 加解密
  - 复刻短信登录所需 RSA 公钥加密
- 已实现 `src/suning_biu_ha/client.py`
  - 运行时抓取登录页并提取公钥与流程常量
  - 支持 `needVerifyCode.do`、`sendCode.do`、`ids/smartLogin/sms`
  - 支持 Cookie 与登录状态持久化
  - 支持 `shcss` / `itapig` 的 SSO 扩散与会话恢复
  - 支持从 HAR 自动提取 App 端已签名模板，并复用到 `families` / `devices`
  - 支持会员信息、家庭列表、设备列表查询
- 已实现 CLI
  - `send-sms`
  - `login`
  - `check`
  - `families`
  - `devices`
  - `keep-alive`
  - 共享参数 `--state-file` / `--har-file` / `--detect` / `--dfp-token` 既可写在子命令前，也可写在子命令后
- 已实现 IAR 本地桥接页
  - 当风控返回 `isIarVerifyCode` 时，程序会申请 IAR ticket
  - 本地起一个 `http://127.0.0.1:<port>/` 链接供用户打开完成拼图
  - 页面会把 token 自动回传给本地进程，继续后续短信发送流程
- 已完成 HAR 结论
  - `clientservices.googleapis.com_2026_03_20_00_33_46.har` 中 `iar-web/validate.json` 返回 `resp_code=0`
  - 本地 `/callback` 返回 `{"ok": true}`，未发现桥接页吞掉验证码 token 的证据
  - 跨进程实测表明 `check` 可仅靠持久化 Cookie 恢复；`families` 之前失败的根因是 App 端签名头缺失，不是 session 失效
- 已补充验证
  - `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest`
  - `env UV_CACHE_DIR=/tmp/uv-cache uv run python -m compileall src`
  - `env UV_CACHE_DIR=/tmp/uv-cache uv run main.py check --har-file apm.suning.cn_2026_03_19_23_47_23.har`
  - `env UV_CACHE_DIR=/tmp/uv-cache uv run main.py families --har-file apm.suning.cn_2026_03_19_23_47_23.har`
  - `env UV_CACHE_DIR=/tmp/uv-cache uv run main.py devices --family-id 37790 --har-file apm.suning.cn_2026_03_19_23_47_23.har`
  - `env UV_CACHE_DIR=/tmp/uv-cache uv run main.py devices --family-id 4770504 --har-file apm.suning.cn_2026_03_19_23_47_23.har`
  - 直接用实现中的 `SuAES` 解密 HAR 内 `needVerifyCode.do` / `sendCode.do` 返回，确认还原出的 `riskType`、`smsTicket`、`loginTicket` 与抓包链路一致

## Risks

- 当前未实现验证码自动求解，仅支持外部传入 `iar` / `slide` / `image` 的验证码 token
- 其中 `iar` 已支持通过本地桥接页自动回传 token，`slide` / `image` 仍未桥接
- `detect` 与 `dfpToken` 默认使用苏宁网页 JS 失败时的回退值，若服务端后续加强风控，可能需要从真实浏览器环境额外采集并传入
- 当前 `families` / `devices` 仍依赖 HAR 中现成的已签名模板，本轮还没有逆向出 `gsSign` / `signinfo` 的通用生成算法
- `devices --family-id` 只对 HAR 里已经出现过签名模板的 `familyId` 生效；若家庭 ID 变化，需要新的 HAR 或进一步逆向签名算法
- 目前先做到登录、保活与设备列表读取，尚未继续实现空调控制指令
