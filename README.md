# 多智能体客服对话数据合成框架

面向中文家电售后场景的任务型对话生成项目。当前聚焦电话客服场景，围绕维修与安装两类诉求，生成可训练、可回放、可校验的结构化对话样本。

项目通过 `user_agent`、`service_agent`、`DialogueOrchestrator` 协同推进对话；支持自动生成用户隐藏设定，并将结果导出为 `JSONL` 和 `JSON`。

## 适用场景

- 生成中文客服训练数据
- 构造维修 / 安装类电话对话样本
- 模拟信息补采流程，例如手机号、地址、姓氏、诉求类型
- 为同一基础场景扩样，生成多条变体对话
- 为用户侧补齐隐藏设定，并做历史去重与相似度控制

## 核心能力

- 支持两类请求：`fault`、`installation`
- 支持场景级异步并发生成
- 支持自动补齐 `customer`、`request`、`hidden_context`
- 支持隐藏设定历史库持久化与去重控制
- 支持输出结构化 transcript 和可直接阅读的完整文本
- 内置基础对话校验逻辑
- 覆盖单元测试

## 地址机制

地址环节是当前项目里最复杂的一段逻辑，分为“隐藏设定生成”“用户回复计划”“客服收集与确认”“校验兜底”四层。

### 1. 隐藏设定生成

- 用户真实地址会先经过完整度校验，不完整地址会直接判无效并重生成。
- 当前默认要求地址至少包含：
  - `city`
  - 非直辖市场景下的 `province`
  - `district/县`
  - `locality`，例如街道、路名、小区、村、地标等
  - 可定位到上门位置的精细信息，例如 `栋/单元/层/室`、门牌号、乡村 `组/号`
- 当前支持几类地址形态：
  - `standard_residential`
  - `house_number_only`
  - `rural_group_number`
  - `landmark_poi`
- 若客服“已知地址”，`service_known_address_value` 会保存一条完整可确认地址，不允许只保存局部地址片段。
- 若客服“已知地址但地址错误”，系统会同时生成：
  - `service_known_address_mismatch_start_level`
  - `service_known_address_rewrite_levels`
  - `service_known_address_correction_value`
- 如果错误从 `province`、`city` 或 `district` 开始，当前策略会从该层级向下整段重塑，不只改一小段细节。

### 2. 用户回复计划

- 地址可以按多轮计划逐步补充，计划保存在 `address_input_rounds`。
- 如果客服已知地址但地址错了，后续地址补充会优先围绕纠正值组织，而不是继续沿用旧地址。
- `user_agent` 提示词中会显式暴露：
  - 客服是否已知地址
  - 已知地址内容
  - 已知地址是否正确
  - 错误起始粒度
  - 需要重塑的粒度链路
  - 本轮应补充的地址片段
- 地址环节允许轻微答偏，但不会无限持续；非电话、非地址槽位则被硬限制为最多 2 轮答偏后必须直接回答。

### 3. 客服收集与确认

- 如果当前需要收集地址且 `service_known_address_value` 存在，客服会直接按已知地址发起确认。
- 这里确认的必须是完整地址，而不是“龙城花园南街62号”这类局部片段。
- 用户确认地址正确时，地址槽会写入真实地址。
- 用户否认地址时，系统会尝试从否认句中抽取纠正地址片段，并与当前确认地址做安全合并。
- 合并规则的关键点：
  - 可以继承高粒度前缀，例如省、市、区
  - 不能把用户没有重新说出的旧细粒度信息自动补回去
  - 如果用户改的是 `district` 及以上，下面的地址链路视为需要重塑
  - 如果用户只改房号、栋号等细节，会做对应替换
- 如果合并后的地址已经足够完整，会立即再次确认。
- 如果还不完整，会按缺失层级追问，例如：
  - 缺区县：追问区县
  - 有区县但缺 locality：追问小区/街道/村
  - 有 locality 但缺门牌：追问几栋几单元几楼几号
- 对乡村地址会单独处理：
  - 如果识别为村、组、队等乡村地址，不会强行按城市住宅追问楼栋单元
  - 如果用户明确说“村里没栋没单元”，追问会切换到“具体到门牌号”

### 4. 地址解析与完整判定

- 地址会被拆成这些组件：
  - `province`
  - `city`
  - `district`
  - `town`
  - `road`
  - `community`
  - `building`
  - `unit`
  - `floor`
  - `room`
- 对地址做匹配时，系统同时使用：
  - 标准化文本比对
  - 组件级比对
  - 精度要求比对
- 如果真实地址里存在 `building`、`unit`、`room`、乡村 `组` 或门牌 `号`，候选地址不能缺这些关键精度信息。
- 对“看起来是同一地址但表达不够全”的情况，确认前会尽量提升为更完整的规范版本。
- 例如当前支持识别 `东信花园五期` 这类带“几期”的小区表达，不会在组件解析时把“`五期`”丢掉。

### 5. 校验兜底

- 生成结果会经过基础 validator 检查。
- 已确认地址后，如果用户又重复地址、故障、电话等旧信息，会被标记为异常样本。
- 如果在同一槽位上连续多次答非所问，或者反复复读上一轮偏题内容，也会被标记为异常样本。

## 工作方式

完整流程如下：

1. `ScenarioFactory` 读取场景文件，并在需要时扩样到指定 `count`
2. 若场景缺少 `call_start_time`，自动补一个随机通话开始时间
3. 若启用 `--auto-hidden-settings`，`HiddenSettingsTool` 先生成用户隐藏设定并写入历史库
4. `service_agent` 先构造“用户首句”，再给出首轮客服回复
5. `user_agent` 与 `service_agent` 按轮次推进，对话中持续补采槽位
6. `DialogueOrchestrator` 汇总 transcript、槽位、状态和校验结果
7. `exporter` 将结果写入 `JSONL` 与 `JSON`

并发粒度是“场景级别并发”。单条对话内部仍按轮次串行推进。

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

## 安装

```bash
pip install -r requirements.txt
```

当前依赖：

- `httpx`
- `openai`
- `python-dotenv`

## 快速开始

### 1. 准备环境变量

项目会从仓库根目录读取 `.env`。

建议至少配置：

```dotenv
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=<your-openai-compatible-base-url>
OPENAI_API_KEY=<your-api-key>
OPENAI_USER=<optional-user-id>
```

如需为不同 agent 指定不同模型：

```dotenv
USER_AGENT_MODEL=<model-for-user-agent>
SERVICE_AGENT_MODEL=<model-for-service-agent>
```

### 2. 生成对话数据

```bash
python -m multi_agent_data_synthesis.cli generate \
  --count 10 \
  --auto-hidden-settings \
  --show-dialogue \
  --show-persona \
  --concurrency 5
```

默认输出：

- `outputs/dialogues.jsonl`
- `outputs/dialogues.json`

### 3. 仅生成隐藏设定

```bash
python -m multi_agent_data_synthesis.cli generate-hidden-settings \
  --count 10 \
  --concurrency 5
```

默认输出：

- `outputs/generated_hidden_scenarios.json`

## CLI 用法

### `generate`

批量生成完整对话样本。

```bash
python -m multi_agent_data_synthesis.cli generate [options]
```

常用参数：

- `--scenario-file`：场景文件路径，默认 `data/seed_scenarios.json`
- `--count`：生成样本数；不传时使用场景文件中的全部场景
- `--jsonl-output`：JSONL 输出路径，默认 `outputs/dialogues.jsonl`
- `--json-output`：JSON 输出路径，默认 `outputs/dialogues.json`
- `--auto-hidden-settings`：生成前自动补齐隐藏设定
- `--show-dialogue`：在终端打印逐轮对话
- `--show-persona`：配合 `--show-dialogue` 使用，额外打印初始用户画像与说话方式
- `--concurrency`：覆盖默认并发数

### `generate-hidden-settings`

仅为场景生成隐藏设定，不执行完整对话合成。

```bash
python -m multi_agent_data_synthesis.cli generate-hidden-settings [options]
```

常用参数：

- `--scenario-file`：场景文件路径，默认 `data/seed_scenarios.json`
- `--count`：生成场景数；不传时使用场景文件中的全部场景
- `--output`：输出路径，默认 `outputs/generated_hidden_scenarios.json`
- `--concurrency`：覆盖默认并发数

## 场景文件格式

场景文件必须是 JSON 数组，元素结构与 `Scenario` 对应。

示例：

```json
[
  {
    "scenario_id": "sample_fault_001",
    "product": {
      "brand": "美的",
      "model": "KF-01",
      "category": "空气能热水器",
      "purchase_channel": "京东"
    },
    "customer": {
      "full_name": "张三",
      "surname": "张",
      "phone": "13800000001",
      "address": "上海市浦东新区测试路1号",
      "persona": "普通用户",
      "speech_style": "简洁"
    },
    "request": {
      "request_type": "fault",
      "issue": "启动后显示E4，热水不出来",
      "desired_resolution": "尽快安排维修",
      "availability": "明天下午"
    },
    "call_start_time": "09:15:00",
    "hidden_context": {},
    "required_slots": [
      "issue_description",
      "surname",
      "phone",
      "address",
      "request_type"
    ],
    "max_turns": 20,
    "tags": [
      "sample"
    ]
  }
]
```

字段说明：

- `scenario_id`：场景唯一标识
- `product`：产品信息
- `customer`：用户基础信息
- `request`：诉求信息，`request_type` 目前支持 `fault` 和 `installation`
- `call_start_time`：可选；为空时自动生成
- `hidden_context`：可选；用户隐藏设定
- `required_slots`：期望在对话中采集到的槽位
- `max_turns`：该场景的最大轮次上限
- `tags`：可选标签

注意事项：

- `product.category` 不能为空，否则会触发校验错误
- 若 `count` 大于场景文件中的条数，系统会对原始场景扩样，并生成新的 `scenario_id`
- 当场景中同时存在 `fault` 和 `installation` 两类样本时，扩样会按 `INSTALLATION_REQUEST_PROBABILITY` 控制采样比例
- 启用 `--auto-hidden-settings` 后，生成结果会覆盖原场景中的部分 `customer`、`request`、`hidden_context`
- 当前实现会对 `required_slots` 做运行时过滤，`product_model`、`availability`、`purchase_channel` 不会作为最终必采槽位参与完成度判断

## 输出结构

每条样本都会导出为一个 `DialogueSample`，核心字段包括：

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

字段含义：

- `status`：`completed` 或 `incomplete`
- `transcript` / `dialogue_process`：结构化轮次列表，话者会被导出为“用户”或“客服”
- `dialogue_text`：拼接后的可读文本
- `collected_slots`：对话中采集到的槽位
- `missing_slots`：仍未采集到的必需槽位
- `validation`：基础校验结果，包含 `passed`、`issues`、`required_slots_complete`
- `related_info`：聚合后的产品、用户、诉求、隐藏设定和校验信息

导出行为：

- `write_jsonl` 采用追加模式；重复执行会继续向文件末尾追加
- `write_json` 采用覆盖模式；每次执行都会覆盖目标文件

## 测试

运行全部单元测试：

```bash
pytest -q
```

地址相关的核心回归入口：

```bash
pytest -q tests/test_hidden_settings_tool.py
pytest -q tests/test_service_policy.py
pytest -q tests/test_validator.py
```

这几组测试主要覆盖：

- 地址完整度校验
- 客服已知地址的确认逻辑
- 错误地址的重塑与多轮补采
- 乡村地址与非标准地址
- 地址确认后的重复信息校验
- 隐藏设定历史默认写入 `data/hidden_settings_history.jsonl`

## 配置项

除模型相关参数外，常用配置主要分为以下几类。

### 生成与请求控制

- `DEFAULT_TEMPERATURE`：默认采样温度，默认 `0.7`
- `REQUEST_TIMEOUT`：请求超时秒数，默认 `90`
- `MAX_ROUNDS`：单条对话最大轮次，默认 `20`
- `MAX_CONCURRENCY`：默认并发数，默认 `5`
- `MODEL_REQUEST_PROFILES`：按模型名覆盖请求参数的 JSON 配置

### 对话行为控制

- `SERVICE_OK_PREFIX_PROBABILITY`：客服回复前缀“好的，”的概率
- `SECOND_ROUND_INCLUDE_ISSUE_PROBABILITY`：用户第 2 轮是否顺带补充问题描述的概率
- `INSTALLATION_REQUEST_PROBABILITY`：扩样时安装类场景的采样概率

### 电话与地址采集控制

- `CURRENT_CALL_CONTACTABLE_PROBABILITY`
- `PHONE_COLLECTION_SECOND_ATTEMPT_PROBABILITY`
- `PHONE_COLLECTION_THIRD_ATTEMPT_PROBABILITY`
- `PHONE_COLLECTION_INVALID_SHORT_PROBABILITY`
- `PHONE_COLLECTION_INVALID_LONG_PROBABILITY`
- `PHONE_COLLECTION_INVALID_PATTERN_PROBABILITY`
- `PHONE_COLLECTION_INVALID_DIGIT_MISMATCH_PROBABILITY`
- `SERVICE_KNOWN_ADDRESS_PROBABILITY`
- `SERVICE_KNOWN_ADDRESS_MATCHES_PROBABILITY`
- `ADDRESS_COLLECTION_FOLLOWUP_PROBABILITY`
- `ADDRESS_SEGMENTED_REPLY_PROBABILITY`
- `ADDRESS_SEGMENT_ROUNDS_WEIGHTS`
- `ADDRESS_SEGMENT_MERGE_STRATEGY_WEIGHTS`
- `ADDRESS_INPUT_OMIT_PROVINCE_CITY_SUFFIX_PROBABILITY`
- `ADDRESS_CONFIRMATION_DIRECT_CORRECTION_PROBABILITY`

### 隐藏设定去重控制

- `HIDDEN_SETTINGS_SIMILARITY_THRESHOLD`：最大相似度阈值，默认 `0.82`
- `HIDDEN_SETTINGS_DUPLICATE_THRESHOLD`：最大字段重复率阈值，默认 `0.5`
- `HIDDEN_SETTINGS_MAX_ATTEMPTS`：生成最大重试次数，默认 `6`
- `HIDDEN_SETTINGS_MULTI_FAULT_PROBABILITY`：多故障描述出现概率

## 测试

```bash
python -m unittest
```

## 当前边界

- 当前领域主要围绕家电售后电话场景
- 当前入口以 CLI 为主，没有提供 Web 服务层
- 当前校验是规则型基础校验，不是完整质检系统
- README 中的能力说明以仓库当前实现为准，不包含外部服务可用性保证
