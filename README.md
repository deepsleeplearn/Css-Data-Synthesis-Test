# 客服任务型对话数据生成框架

这是一个面向中文客服场景的多智能体数据合成项目，当前聚焦家电售后领域，支持批量生成维修与安装类电话对话数据。

项目通过 `user_agent`、`service_agent` 和 `orchestrator` 协同工作，输出结构化对话、拼接文本和槽位采集结果；也支持为用户侧自动生成隐藏设定，并通过历史库做重复度与相似度控制。

## 当前能力

- 批量生成中文客服通话对话样本
- 支持两类请求：`fault` 和 `installation`
- 支持按场景级别异步并发生成
- 支持自动补齐用户隐藏设定
- 支持将隐藏设定写入 JSONL 历史库并做去重控制
- 支持导出 `JSONL` 和 `JSON`
- 覆盖基础单元测试

## 项目结构

```text
multi_agent_data_synthesis/
  agents.py
  cli.py
  config.py
  dialogue_plans.py
  exporter.py
  hidden_settings_tool.py
  llm.py
  orchestrator.py
  prompts.py
  scenario_factory.py
  schemas.py
  service_policy.py
  static_utterances.py
  validator.py
data/
  seed_scenarios.json
  hidden_settings_history.jsonl
tests/
  ...
requirements.txt
README.md
```

## 处理流程

1. `ScenarioFactory` 读取场景文件，并按 `count` 扩展样本数。
2. `DialogueOrchestrator` 初始化用户与客服 agent。
3. 如启用 `--auto-hidden-settings`，先由 `HiddenSettingsTool` 生成用户隐藏设定。
4. `service_agent` 生成首轮确认话术，随后双方按轮次推进。
5. `orchestrator` 合并槽位、检查结束条件、执行校验并导出结果。

并发粒度是“场景级别并发”。单条对话内部仍按轮次串行推进。

## 安装

```bash
pip install -r requirements.txt
```

当前依赖很轻量：

- `httpx`
- `openai`
- `python-dotenv`

## 配置

项目会在仓库根目录读取 `.env`。仓库当前没有提供 `.env.example`，需要手动创建。

最少建议配置：

```dotenv
OPENAI_MODEL=<your-model>
OPENAI_BASE_URL=<your-openai-compatible-base-url>
OPENAI_API_KEY=<your-api-key>
OPENAI_USER=<optional-user-id>
```

如需拆分模型，也可以单独指定：

```dotenv
USER_AGENT_MODEL=<model-for-user-agent>
SERVICE_AGENT_MODEL=<model-for-service-agent>
```

### 常用可选配置

#### 生成与请求控制

- `DEFAULT_TEMPERATURE`: 默认采样温度，默认 `0.7`
- `REQUEST_TIMEOUT`: 请求超时秒数，默认 `90`
- `MAX_ROUNDS`: 单条对话最大轮次，默认 `20`
- `MAX_CONCURRENCY`: 默认并发数，默认 `5`
- `MODEL_REQUEST_PROFILES`: 按模型名覆盖请求体参数的 JSON 配置

#### 对话行为控制

- `SERVICE_OK_PREFIX_PROBABILITY`: 客服回复前缀“好的，”的概率
- `SECOND_ROUND_INCLUDE_ISSUE_PROBABILITY`: 用户第 2 轮是否顺带补充问题描述的概率
- `INSTALLATION_REQUEST_PROBABILITY`: 扩样时安装类场景被采样到的概率

#### 电话与地址采集控制

- `CURRENT_CALL_CONTACTABLE_PROBABILITY`: 当前来电号码可联系到用户的概率
- `PHONE_COLLECTION_SECOND_ATTEMPT_PROBABILITY`: 需要第 2 次拨号盘输入才成功的概率
- `PHONE_COLLECTION_THIRD_ATTEMPT_PROBABILITY`: 需要第 3 次拨号盘输入才成功的概率
- `PHONE_COLLECTION_INVALID_SHORT_PROBABILITY`: 错误短号权重
- `PHONE_COLLECTION_INVALID_LONG_PROBABILITY`: 错误长号权重
- `PHONE_COLLECTION_INVALID_PATTERN_PROBABILITY`: 错误格式号码权重
- `SERVICE_KNOWN_ADDRESS_PROBABILITY`: 客服侧预置地址的概率
- `SERVICE_KNOWN_ADDRESS_MATCHES_PROBABILITY`: 预置地址与真实地址一致的概率
- `ADDRESS_COLLECTION_FOLLOWUP_PROBABILITY`: 地址补采集跟进概率
- `ADDRESS_CONFIRMATION_DIRECT_CORRECTION_PROBABILITY`: 用户在否定地址时直接给出正确地址的概率

#### 隐藏设定去重控制

- `HIDDEN_SETTINGS_SIMILARITY_THRESHOLD`: 最大相似度阈值，默认 `0.82`
- `HIDDEN_SETTINGS_DUPLICATE_THRESHOLD`: 最大重复率阈值，默认 `0.5`
- `HIDDEN_SETTINGS_MAX_ATTEMPTS`: 隐藏设定生成最大重试次数，默认 `6`
- `HIDDEN_SETTINGS_MULTI_FAULT_PROBABILITY`: 多故障描述出现概率

## 使用方式

### 生成对话数据

```bash
python -m multi_agent_data_synthesis.cli generate --count 10 --auto-hidden-settings --concurrency 5
```

常用参数：

- `--scenario-file`: 场景文件路径，默认 `data/seed_scenarios.json`
- `--count`: 生成数量；为空时使用场景文件中的全部场景
- `--jsonl-output`: JSONL 输出路径，默认 `outputs/dialogues.jsonl`
- `--json-output`: JSON 输出路径，默认 `outputs/dialogues.json`
- `--auto-hidden-settings`: 自动生成用户隐藏设定
- `--show-dialogue`: 在终端打印逐轮对话
- `--concurrency`: 覆盖默认并发数

### 仅生成隐藏设定

```bash
python -m multi_agent_data_synthesis.cli generate-hidden-settings --count 10 --concurrency 5
```

常用参数：

- `--scenario-file`: 场景文件路径
- `--count`: 生成数量
- `--output`: 输出路径，默认 `outputs/generated_hidden_scenarios.json`
- `--concurrency`: 覆盖默认并发数

## 输入数据格式

场景文件需要是 JSON 数组，元素结构与 `Scenario` 对应。示意如下：

```json
[
  {
    "scenario_id": "sample_fault_001",
    "product": {
      "brand": "<brand>",
      "model": "<model>",
      "category": "<category>",
      "purchase_channel": "<channel>"
    },
    "customer": {
      "full_name": "<name>",
      "surname": "<surname>",
      "phone": "<phone>",
      "address": "<address>",
      "persona": "<persona>",
      "speech_style": "<speech_style>"
    },
    "request": {
      "request_type": "fault",
      "issue": "<issue>",
      "desired_resolution": "<desired_resolution>",
      "availability": "<availability>"
    },
    "required_slots": [
      "issue_description",
      "surname",
      "phone",
      "address"
    ],
    "max_turns": 20,
    "tags": [
      "sample"
    ]
  }
]
```

说明：

- `call_start_time` 为空时会自动补生成
- `required_slots` 会在运行时结合 `request_type` 做有效槽位过滤
- `tags` 可为空
- 若启用自动隐藏设定，`customer`、`request` 和 `hidden_context` 可能被生成结果覆盖

## 输出说明

默认会生成两个文件：

- `outputs/dialogues.jsonl`
- `outputs/dialogues.json`

每条样本包含这些核心字段：

- `scenario_id`
- `status`
- `rounds_used`
- `transcript`
- `dialogue_process`
- `dialogue_text`
- `collected_slots`
- `missing_slots`
- `scenario`
- `validation`
- `related_info`

其中：

- `transcript` / `dialogue_process` 是结构化轮次列表
- `dialogue_text` 是可直接阅读的完整文本
- `related_info` 汇总产品信息、用户信息、诉求、隐藏设定、槽位采集和校验结果

需要注意：

- `write_jsonl` 以追加模式写入；重复执行会持续往同一个 `JSONL` 文件末尾追加
- `write_json` 会覆盖目标文件
- 隐藏设定历史默认写入 `data/hidden_settings_history.jsonl`

## 测试

```bash
python -m unittest
```

当前仓库测试已覆盖配置加载、场景扩展、编排流程、校验逻辑、服务策略和隐藏设定工具。

## 当前限制

- 当前生成逻辑仍聚焦单一业务域，不是通用多行业对话平台
- 单条对话按轮次串行执行，无法在单会话内部并行
- 隐藏设定去重依赖本地 JSONL 历史库，不适合高并发分布式场景
- 项目当前更偏“数据生成骨架”，尚未内置独立质检 agent、改写 agent 和评测流水线
