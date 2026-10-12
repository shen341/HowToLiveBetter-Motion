# ADR-011: 令牌桶速率控制与多级指数退避重试容灾架构 (Rate Limiting and Exponential Backoff Architecture)

## 状态 (Status)
**Accepted (已采纳实施)**

## 日期 (Date)
2026-10-12

## 背景与上下文 (Context)
在流水线进行大规模批量生成（如使用 `--limit 50` 批量处理多个条目，每条包含 1 篇分镜脚本、6 张艺术原画、6 段 TTS 语音）时，系统需要向外部 AI 服务密集发起多次网络请求：
1. **境外 API 速率限制 (HTTP 429)**：Muse AI 开放平台和 Cloudflare Edge-TTS 均对客户端请求设有 RPM（每分钟请求数）与并发连接数阈值；
2. **偶发网络抖动与网关异常 (HTTP 502/503/504)**：跨境网络存在偶发的 TCP 握手超时、网关超时或服务暂时不可用；
3. **传统脆弱性痛点**：若缺乏并发保护与智能重试机制，单个分镜或语音请求一旦触发 429 或网络超时，就会直接抛出未捕获异常，导致整个批处理进程被暴力终止，未完成条目被迫中断，破坏了流水线的无人值守稳定性。

## 架构决策 (Decision)

### 1. 纯 Python 线程安全令牌桶速率控制器 (`TokenBucketLimiter`)
在 `src/rate_limiter.py` 中自主实现轻量级令牌桶算法（Token Bucket）：
- **核心参数**：
  - `rate_per_minute`（默认 Muse AI 30 RPM，Edge-TTS 60 RPM）；
  - `capacity`（最大突发桶深，默认 $2 \times \text{refill\_rate}$）。
- **非阻塞与超时等待 (`acquire`)**：
  - 基于高精度 `time.monotonic()` 动态计算时间增量补齐令牌；
  - 令牌充足时无损通过；令牌暂时耗尽时，计算确切缺口时间精准休眠（`time.sleep`），超时（默认 45~60s）未获取则熔断提示；
  - 线程互斥锁（`threading.Lock`）保证多线程/多协程安全。

### 2. 智能分类与指数退避重试引擎 (`retry_with_backoff`)
构建统一请求执行器，接管 `MuseClient`（`generate_script`、`generate_image`）与 `TTSClient`（`generate_speech`）的底层网络调用：
- **瞬时错误识别器 (`is_transient_error`)**：
  - **允许重试的瞬时异常**：
    - HTTP 429（Too Many Requests / 限流）；
    - HTTP 500、502、503、504（服务端暂时性宕机/网关超时）；
    - `requests.exceptions.Timeout`、`ConnectionError`、`openai.APITimeoutError`、`APIConnectionError`；
  - **快速失败的永久错误 (Fast-Fail)**：
    - HTTP 400（参数格式错误）、HTTP 401（API Key 密钥失效）、HTTP 403（权限拒绝）、HTTP 404；此类错误不应重试，立即向上抛出，避免无谓消耗配额与阻塞时间。
- **动态延迟与抖动退避计算**：
  - 遵循经典指数退避序列：$t = t_{base} \times \alpha^{attempt - 1} + \Delta_{jitter}$（初始 $2.0\text{s} \to 4.0\text{s} \to 8.0\text{s}$）；
  - **尊重 `Retry-After`**：如果 HTTP 响应头携带 `Retry-After: N`，自动优先以服务端的冷却要求为准；
  - **随机抖动 (Jitter)**：附加 $0.1 \sim 0.6\text{s}$ 随机扰动，防止多并发重试时的惊群效应（Thundering Herd）。

### 3. 多级容灾降级与断点隔离
- 若连续 3 次重试仍未成功：
  - `MuseClient` 记录详细警告，自动安全降级至内置高质量规则分镜与风格占位图，确保素材管线不崩溃；
  - `02_ai_generator.py` 捕获单条异常，记录完整异常堆栈至 SQLite 的 `error_message`，递增 `retry_count`，并标记为 `Failed`，整批主循环不受影响，继续执行下一条目。

### 4. 环境配置与命令行参数支持
- 环境变量（`.env`）支持全局默认覆盖：
  `RATE_LIMIT_MUSE_RPM=30`、`RATE_LIMIT_TTS_RPM=60`、`API_MAX_RETRIES=3`、`API_RETRY_DELAY=2.0`；
- 命令行参数支持运行期覆盖：
  `--rpm-muse 30`、`--rpm-tts 60`、`--max-retries 3`。

---

## 备选方案评估 (Alternatives Considered)

### 备选方案 A：引入第三方库 `tenacity` 或 `ratelimit`
- **缺点**：增加了外部依赖和包体积；且 `tenacity` 默认重试对 requests/openai 自定义响应头（如 `Retry-After`）的动态解析不够原生，容易导致配置僵硬。
- **结论**：**否决（纯原生标准库实现，零外部臃肿依赖）**。

### 备选方案 B：简单在循环中加固定 sleep（如 `time.sleep(2)`）
- **缺点**：无差别降低吞吐量，正常请求也变慢，而在遇到突发 429 时又不够休眠，无法根本解决问题。
- **结论**：**否决**。

---

## 实施后果与收益 (Consequences)

### 正面收益
1. **大批量运行无人值守保障**：在 `--limit 50` 批量执行时，瞬时网络抖动和限流被自动吸收消化，任务成功率大幅提升；
2. **保护外部 API 账户安全**：严格控制发包速率在安全阈值（RPM）内，避免触发服务商的滥用封禁规则；
3. **故障上下文高度可观测**：发生重试时在终端输出清晰的等待时长与重试原因，失败时完整保留 SQLite 错误记录；
4. **自动化测试防护**：配套编写 `tests/test_rate_limiter.py` 覆盖 8 个测试用例，杜绝重构破坏。
