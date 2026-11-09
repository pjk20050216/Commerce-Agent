# 多智能体电商购物助手

一套多 Agent 协作运行时，同时服务**商家侧内容生产**与**消费者侧购物决策**：

- **商家侧**：LangGraph 状态图编排 7 个专业 Agent，从商品理解、创意策划、视觉设计，
  到图片/视频生成、质量审核，再接入刊登链路完成素材优化、多语言文案、平台合规检查与推送上架；
- **消费者侧**：另外 10 个 Agent 组成「虚拟买手团」「售后纠纷仲裁庭」「直播购物分身」，
  覆盖协同选品比价、差评排雷、纠纷举证与直播间的实时决策辅助。

两侧共用同一个 FastAPI 服务与同一套多租户数据隔离，全过程状态可追踪、可恢复、可复盘。

> 视觉生成、刊登工具、消费者侧三套能力、RAG 知识增强、AI 会话追踪共用同一个服务与同一套数据模型。

## 为什么需要多 Agent 编排

单 Agent 直接对话在电商购物场景会遇到四个硬问题：

| 问题 | 本项目的解法 |
|---|---|
| 一次任务十几个步骤，单 Prompt 无法兼顾 | 拆成 7 个 Agent 串行/条件分支，每步只做一件事，提示词互不污染 |
| 商品分析、创意、出图、审核诉求互相冲突 | 每阶段产出结构化 Pydantic 模型，下游只消费上游结构，不靠自然语言转述 |
| 图片/视频生成是长耗时异步任务，容易中断 | Redis 持久化任务状态 + WebSocket 实时推送 + 失败降级为 Mock 占位资产 |
| 刊登到不同平台规则各异（尺寸、字数、禁词） | 平台适配器 + 规则表 + 合规报告，Amazon/eBay/Shopify 各自独立校验 |

## 核心能力

| 能力 | 说明 | 关键实现 |
|---|---|---|
| 多 Agent 编排 | Orchestrator → 需求分析 → 创意策划 → 视觉设计 → 图片/视频生成 → 质量审核 | [`src/graph/workflow.py`](src/graph/workflow.py)、[`src/agents/`](src/agents/) |
| 条件路由 | 按 `image_only` / `video_only` / `image_and_video` 走不同分支；任一阶段失败即短路到 END | [`src/graph/workflow.py`](src/graph/workflow.py) |
| 状态累加 | 列表字段用 `Annotated[list, add]`，多节点写入不覆盖历史 | [`src/graph/state.py`](src/graph/state.py) |
| 商品理解 | 卖点提取、类目推荐、目标人群分析，输出 `RequirementReport` | [`src/agents/requirement_analyzer.py`](src/agents/requirement_analyzer.py) |
| 创意策划 | 主题、视觉风格、配色方案、目标情绪 | [`src/agents/creative_planner.py`](src/agents/creative_planner.py)、[`src/models/creative.py`](src/models/creative.py) |
| 视觉设计 | 主图/场景图/卖点图提示词 + 视频分镜脚本 | [`src/agents/visual_designer.py`](src/agents/visual_designer.py)、[`src/models/storyboard.py`](src/models/storyboard.py) |
| 图片生成 | 多模型通道，异步任务 + 回调/轮询，产物落本地或 OSS | [`src/agents/image_generator.py`](src/agents/image_generator.py)、[`src/clients/`](src/clients/) |
| 视频生成 | 分镜转视频，JWT 鉴权 + 异步轮询 | [`src/agents/video_generator.py`](src/agents/video_generator.py)、[`src/clients/kling_video_client.py`](src/clients/kling_video_client.py) |
| 质量审核 | 清晰度/构图/色彩/相关性四维评分与问题清单 | [`src/agents/quality_reviewer.py`](src/agents/quality_reviewer.py)、[`src/models/assets.py`](src/models/assets.py) |
| 多平台刊登 | 商品导入 → 素材优化 + 文案生成（并行）→ 合规检查 → 推送 | [`src/graph/listing_workflow.py`](src/graph/listing_workflow.py)、[`src/agents/listing_*.py`](src/agents/) |
| 平台适配器 | Amazon（含 US/UK/JP/DE 分站）、eBay、Shopify，可注册可扩展 | [`src/agents/listing_platform_adapter.py`](src/agents/listing_platform_adapter.py)、[`src/agents/listing_amazon_adapter.py`](src/agents/listing_amazon_adapter.py) |
| 合规检查 | 广告法禁词 + 平台规则（主图白底、尺寸、标题字数、五点描述） | [`src/agents/listing_compliance_checker.py`](src/agents/listing_compliance_checker.py)、[`src/agents/listing_compliance_rules.py`](src/agents/listing_compliance_rules.py) |
| RAG 知识增强 | 品牌规范、类目知识、成功案例、合规规则检索注入 Agent 上下文 | [`src/rag/`](src/rag/)、[`src/agents/rag_*.py`](src/agents/) |
| 知识库 Agent | 查询分析 → 策略路由 → 混合检索 → RRF 融合 → 答案生成 | [`src/knowledge/agent_workflow.py`](src/knowledge/agent_workflow.py) |
| 知识图谱 | 文档摄入抽取实体/关系，内存图谱 + 文档入库 | [`src/knowledge/graph.py`](src/knowledge/graph.py)、[`src/knowledge/ingestion.py`](src/knowledge/ingestion.py) |
| Agent 可观测 | DAG 流程图 + 提示词轨迹 + 输入输出 + 子调用 + Token/费用 | [`frontend/src/components/workbench/`](frontend/src/components/workbench/) |
| 实时推送 | 任务状态经 WebSocket 推送前端，无需轮询 | [`src/api/router/tasks.py`](src/api/router/tasks.py) |
| 多租户隔离 | 全部查询按 `tenant_id` 过滤，API Token（SHA256 + Scope）鉴权 | [`src/auth/`](src/auth/)、[`src/db/repository.py`](src/db/repository.py) |
| 模型厂商管理 | DB 驱动 + Settings 回退，支持运行时切换与连通性测试 | [`src/api/router/model_providers.py`](src/api/router/model_providers.py)、[`src/clients/provider_factory.py`](src/clients/provider_factory.py) |
| 虚拟买手团 | 风格顾问 ‖ 性价比分析师 ‖ 质检员三路并行 → 决策官合成买手决策卡（评分 / 理由 / 预警） | [`src/graph/buyer_workflow.py`](src/graph/buyer_workflow.py)、[`src/agents/buyer_style_advisor.py`](src/agents/buyer_style_advisor.py) |
| 全网比价 | ES 价格索引 / 独立采集服务 / 模拟数据三级降级，历史价格曲线与低位判断 | [`src/clients/price_search.py`](src/clients/price_search.py)、[`src/agents/price_analysis.py`](src/agents/price_analysis.py) |
| 纠纷仲裁庭 | 事实还原 → 规则库匹配（附法条）→ 三套维权话术，输出责任方与置信度 | [`src/graph/dispute_workflow.py`](src/graph/dispute_workflow.py)、[`src/agents/dispute_rules.py`](src/agents/dispute_rules.py) |
| 直播购物分身 | 口播关键信息抽取 + 弹幕情感口碑 + 报价触发一键比价，增量快照 + WebSocket | [`src/graph/live_workflow.py`](src/graph/live_workflow.py)、[`src/agents/live_subtitle_summarizer.py`](src/agents/live_subtitle_summarizer.py) |
| AI 会话追踪 | Token 消耗、双币种费用估算、按模型/Agent 分解 | [`src/api/router/conversation.py`](src/api/router/conversation.py)、[`src/db/conversation_models.py`](src/db/conversation_models.py) |

## 架构

```
浏览器 / 管理后台（Vue 3 + Element Plus，16 个页面）
        │  REST + WebSocket
        ▼
FastAPI（uvicorn）
        │
        ├── /api/v1/products /tasks /assets /dashboard     商品、任务、资产、仪表盘
        ├── /api/v1/listing/*                              刊登、合规、适配器配置
        ├── /api/v1/buyer/*                                买手决策卡、全网比价
        ├── /api/v1/dispute/*                              纠纷仲裁、维权话术
        ├── /api/v1/live/*                                 直播会话、增量快照、一键比价
        ├── /api/v1/knowledge/* /evaluation/*              知识库、图谱、RAG 评估
        ├── /api/v1/ai/* /model-providers                  会话追踪、厂商管理
        └── /api/v1/tasks/{id}/ws                           WebSocket 实时状态
                                                          /api/v1/live/sessions/{id}/ws
        │
        ▼
┌───────────────── LangGraph 运行时 ─────────────────┐
│  视觉生成工作流                                     │
│    Orchestrator → RequirementAnalyzer →            │
│    CreativePlanner → VisualDesigner →              │
│    [ImageGenerator | VideoGenerator] →             │
│    QualityReviewer → END                           │
│                                                     │
│  刊登工作流                                         │
│    ImportProduct → [AssetOptimizer ‖ Copywriter] → │
│    ComplianceChecker → PlatformPush → END          │
│                                                     │
│  知识库工作流                                       │
│    QueryAnalyzer → StrategyRouter →                │
│    HybridRetriever → RRF Fuser → Answer            │
│                                                     │
│  消费者侧工作流                                     │
│    买手团：StyleAdvisor ‖ ValueAnalyst ‖            │
│            QualityInspector → DecisionMaker → END  │
│    仲裁庭：FactRestorer → RuleInterpreter →        │
│            Negotiator → END                        │
│    直播分身：Subtitle → [Danmaku ‖ Price] → Merge   │
└─────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   LLM / 图片 / 视频厂商   PostgreSQL + PGVector   Redis
   （OpenAI 兼容协议）      向量、业务、图谱、会话    任务状态、缓存
```

一次典型生成任务：

```
POST /api/v1/tasks
  → 校验商品存在、写入任务记录（status=pending）
  → 后台 asyncio 任务执行 LangGraph 状态图
  → Orchestrator 初始化状态
  → RequirementAnalyzer 提取卖点 → CreativePlanner 出方案
  → VisualDesigner 产出提示词与分镜
  → ImageGenerator / VideoGenerator 调用厂商（无 Key 则降级 Mock）
  → QualityReviewer 打分与问题清单
  → 资产落库（assets 表）+ 任务置为 completed
  → WebSocket 推送每步状态变化
  → 前端工作台展示 DAG、提示词、Token 与费用
```

## 目录结构

```
src/
  agents/                  25 个 Agent（7 视觉生成 + 4 RAG 增强 + 4 刊登 + 10 消费者侧）
    base.py                Agent 基类（LLM 调用、日志、Token 统计）
    orchestrator.py        编排调度
    requirement_analyzer.py 需求分析
    creative_planner.py    创意策划
    visual_designer.py     视觉设计与分镜
    image_generator.py     图片生成
    video_generator.py     视频生成
    quality_reviewer.py    质量审核
    rag_*.py               RAG 增强版（需求分析 / 创意策划 / 质量审核 / 图片生成）
    listing_*.py           刊登链路（导入、素材、文案、合规、适配器、推送、限流、重试）
    consumer_base.py       消费者侧基类（LLM 可选，缺 Key 时走规则）
    buyer_*.py             虚拟买手团（风格顾问 / 性价比分析师 / 质检员 / 决策官）
    buyer_review_lexicon.py 差评缺陷词库与类目退货率基准
    price_analysis.py      比价结果聚合与性价比折算（买手团与直播共用）
    dispute_*.py           纠纷仲裁（事实还原 / 规则解读 / 话术生成）
    dispute_rules.py       平台争议规则库（含法条摘要）
    live_*.py              直播分身（字幕摘要 / 弹幕情感 / 一键比价）
    live_lexicon.py        口播关键词与弹幕情感词典
  graph/
    state.py               AgentState 定义（含 RAG 与可观测字段）
    workflow.py            视觉生成状态图
    listing_state.py       刊登状态
    listing_workflow.py    刊登状态图（含并行分支）
    buyer_state.py         买手团状态
    buyer_workflow.py      买手团状态图（三路并行）
    dispute_state.py       仲裁庭状态
    dispute_workflow.py    仲裁庭状态图（三段串行）
    live_state.py          直播状态
    live_workflow.py       直播状态图（增量合并）
  models/                  商品、创意、分镜、资产、刊登、买手、纠纷、直播 Pydantic 模型
  api/
    router/                17 个路由模块（health/auth/products/tasks/assets/listing/
                           knowledge/knowledge_graph/evaluation/dashboard/
                           conversation/model_providers/adapter_config/listing_push/
                           buyer/dispute/live）
    schema/                请求/响应 DTO
    service/               Redis 客户端、任务管理器、资产落库、会话记录
  db/                      PostgreSQL 连接、ORM 模型、仓储、向量存储、加密字段、
                           消费者侧三张表（决策卡 / 仲裁案件 / 直播会话）
  rag/                     Embedding、检索器、分块、文档处理、混合检索、重排序、
                           Query 改写、图谱构建/检索、记忆存储与分类
  knowledge/               知识图谱、文档摄入、知识库 Agent 工作流
  auth/                    API Token 鉴权、租户上下文
  clients/                 通义万象、可灵、OpenAI 兼容 LLM/图片、厂商工厂、
                           全网比价数据源（ES / 采集服务 / 模拟）
  storage/                 存储抽象、本地实现、工厂
  config/settings.py       pydantic-settings 配置
frontend/src/
  views/                   19 个页面（仪表盘、商品、任务、工作台、知识库、刊登、
                           虚拟买手团、售后仲裁庭、直播购物分身、厂商…）
  components/workbench/    DAG、详情面板、提示词轨迹、子调用、指标
  api/ types/ stores/      请求封装、类型定义、Pinia 状态
tests/                     719 个测试（agents / api / db / graph / rag / knowledge / storage）
docs-site/                 MkDocs 文档站
```

## 快速开始

### 1. 安装

```bash
# uv 管理依赖（Windows 可直接双击「一键初始化环境.bat」）
uv sync

# 需要本地 RAG（BGE 模型、sentence-transformers）时
uv sync --extra rag
```

### 2. 配置

```bash
cp .env.example .env
```

至少配置一个 LLM/图片/视频厂商密钥（`DASHSCOPE_API_KEY`、`QWEN_API_KEY`、`KLING_ACCESS_KEY` 等）。
**没有密钥也能跑**：`ALLOW_MOCK_ASSETS=true` 时图片与视频自动降级为 Mock 占位资产，适合本地演示与验收。

数据库与 Redis：

```bash
# 仅启动基础设施（PostgreSQL 5432 + pgvector、Redis 6380）
docker compose up -d postgres redis

# 若使用容器 Redis，需把 .env 的 REDIS_URL 改为 redis://localhost:6380/0
```

### 3. 启动

```bash
# 后端（端口 8002，含 /docs）
uv run python main.py

# 前端（端口 5173）
cd frontend && npm install && npm run dev
```

Windows 下可直接双击 **`一键启动.bat`**：自动检查 `.venv` 与前端依赖，分别拉起前后端并打开浏览器；
**`一键停止.bat`** 负责释放端口。

- 管理后台：<http://localhost:5173>
- 接口文档：<http://localhost:8002/docs>
- 健康检查：<http://localhost:8002/api/v1/health>
- 默认账号：`admin / admin123`（由 `scripts/setup_all.bat` 创建）

### 4. 初始化示例数据

```bash
# 建表、创建开发账号、Seed 厂商与知识库
# Windows 直接双击运行 scripts\setup_all.bat
# 其他平台按脚本内的 uv run 命令逐条执行
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health`、`/api/v1/health` | 健康检查 |
| POST | `/api/v1/auth/register`、`/login` | 注册、登录 |
| GET | `/api/v1/auth/me` | 当前身份 |
| GET/POST | `/api/v1/products` | 商品列表 / 创建 |
| GET/PUT/DELETE | `/api/v1/products/{id}` | 商品详情 / 更新 / 删除 |
| POST | `/api/v1/products/{id}/images` | 上传商品图 |
| GET/POST | `/api/v1/tasks` | 任务列表 / 创建生成任务 |
| GET | `/api/v1/tasks/{id}/status` | 任务状态 |
| POST | `/api/v1/tasks/{id}/cancel` | 取消任务 |
| WS | `/api/v1/tasks/{id}/ws` | 任务实时状态推送 |
| GET | `/api/v1/assets`、`/assets/{id}` | 资产查询 / 详情 / 删除 |
| POST | `/api/v1/listing/import-product` | 导入待刊登商品 |
| GET/POST | `/api/v1/listing/tasks` | 刊登任务 |
| POST | `/api/v1/listing/tasks/from-visual` | 由视觉任务直接建刊登任务 |
| POST | `/api/v1/listing/tasks/{id}/compliance` | 执行合规检查 |
| POST | `/api/v1/listing/tasks/{id}/push` | 推送平台 |
| GET | `/api/v1/listing/tasks/{id}/push-results` | 推送结果 |
| GET/POST | `/api/v1/listing/adapter-configs` | 平台适配器配置 |
| POST | `/api/v1/buyer/decisions` | 生成买手决策卡 |
| GET | `/api/v1/buyer/decisions`、`/{card_id}` | 决策卡历史 / 详情 |
| POST | `/api/v1/buyer/compare` | 单独发起全网比价 |
| POST | `/api/v1/dispute/cases` | 提交纠纷仲裁 |
| GET | `/api/v1/dispute/cases`、`/{case_id}` | 案件历史 / 详情 |
| POST | `/api/v1/dispute/cases/{case_id}/draft` | 重新生成指定语气话术 |
| POST | `/api/v1/live/sessions` | 创建直播会话 |
| POST | `/api/v1/live/sessions/{id}/ingest`、`/end` | 推入字幕/弹幕 / 结束会话 |
| GET | `/api/v1/live/sessions`、`/{id}/snapshot` | 会话列表 / 最新快照 |
| WS | `/api/v1/live/sessions/{id}/ws` | 直播快照实时推送 |
| POST | `/api/v1/live/price-check` | 一键比价 |
| GET/POST | `/api/v1/knowledge/documents` | 知识库文档 |
| POST | `/api/v1/knowledge/documents/upload` | 上传文档 |
| POST | `/api/v1/knowledge/search`、`/search/hybrid` | 向量 / 混合检索 |
| POST | `/api/v1/knowledge/agent/query` | 知识库 Agent 问答 |
| GET/POST | `/api/v1/knowledge/graphs` | 知识图谱 |
| GET | `/api/v1/knowledge/stats` | 知识库统计 |
| GET | `/api/v1/evaluation/*` | 命中率、对比、报告、优化建议 |
| GET | `/api/v1/dashboard/stats` | 仪表盘聚合 |
| GET | `/api/v1/ai/conversations`、`/usage/overview` | 会话追踪与用量 |
| GET/POST/PUT/DELETE | `/api/v1/model-providers` | 模型厂商管理 |
| POST | `/api/v1/model-providers/{id}/test` | 厂商连通性测试 |

示例：

```bash
# 创建商品
curl -X POST http://localhost:8002/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"智能运动手表","category":"digital","description":"健康监测与运动追踪","brand":"TechFit"}'

# 创建生成任务
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"product_id":"prod_001","task_type":"image_and_video",
       "image_types":["main","scene","selling_point"],
       "image_count_per_type":1,"video_duration":30.0}'
```

完整交互式文档见 <http://localhost:8002/docs>。

## 刊登链路

从视觉产物到平台上架是一条独立状态图，四个阶段：

1. **ImportProduct**：把视觉商品的 `Product` 转换为刊登用的 `ListingProduct`（`source_images` 留空，由后续填充）；
2. **AssetOptimizer ‖ Copywriter**：素材包与文案包**并行生成**，按平台规范裁剪尺寸、限制张数、控制标题字数；
3. **ComplianceChecker**：按平台规则校验主图白底、尺寸、图片数量、标题长度、五点描述、搜索词字节数，命中禁词记 `WARNING`；
4. **PlatformPush**：适配器推送，带限流与指数退避重试，结果落 `task_results`。

平台适配器通过注册表管理，Amazon 的 US/UK/JP/DE 分站共用同一适配器与素材规范：

```python
registry.register(Platform.AMAZON_US, AmazonAdapter)
registry.register(Platform.EBAY, EbayAdapter)
registry.register(Platform.SHOPIFY, ShopifyAdapter)
```

## 消费者侧：三个场景

三个场景都由 LangGraph 编排，但形态不同：买手团是**并行汇合**，仲裁庭是**串行流水**，
直播分身是**增量合并**。

### 1. 虚拟买手团 —— 协同选品与比价

```
POST /api/v1/buyer/decisions
        │
        ├─ StyleAdvisor          浏览/收藏/加购/购买记录 → 风格偏好与价格带（行为权重 1/2/3/4）
        ├─ ValueAnalyst          全网报价 + 历史曲线 → 现在该不该买
        └─ QualityInspector      差评缺陷词 + 退货率基准 → 质量风险
                  │
                  ▼
            DecisionMaker        加权评分（风格 0.3 / 性价比 0.4 / 质量 0.3）→ 买手决策卡
```

决策卡包含综合评分与三项分解、推荐理由、风险预警（含数据可信度提示）、一句话行动建议。
评分不是「模型感觉」，而是可复算的加权：`总分 = Σ(分项 × 权重) − 风险惩罚`，
分项与权重都会随卡返回，便于复核。

**比价数据源三级降级**（`PRICE_SEARCH_BACKEND=auto` 时按顺序探测）：

| 顺序 | 实现 | 说明 |
|---|---|---|
| 1 | Elasticsearch | 读取自建价格索引 `product_prices`，按天聚合历史最低价 |
| 2 | 采集服务 | `POST {endpoint}/search`、`/history`，本项目只定义契约 |
| 3 | 模拟数据 | 确定性生成，`is_mock=True`，决策卡顶部明确标注「模拟数据」 |

> **关于爬虫**：本项目**不内置**任何站点的抓取实现。抓取第三方商品页涉及目标站点的服务条款与
> robots 协议，合规性取决于具体站点与用途，因此这里只提供采集服务的调用契约与数据结构，
> 由部署方接入合规数据源。模拟数据源的作用是让流程在无外部依赖时可跑通、可测试。

### 2. 售后纠纷仲裁庭 —— 多角度证据链

```
FactRestorer ──▶ RuleInterpreter ──▶ Negotiator
 事实时间线        规则库匹配           投诉 / 申诉 / 协商
 证据缺口          责任方 + 置信度      四段式正文 + 条款引用
```

- **事实还原**：把聊天记录、物流轨迹、开箱凭证归一化为 `E1..En` 证据项，按时间排序，
  并推导 `received` / `opened` / `quality_issue` / `within_seven_days` 等事实标记；
- **规则解读**：14 条平台争议规则按「声明式事实条件」匹配，避免因措辞不同漏判；
  每条规则附法律条款摘要，同向权重占比决定责任方，双方差距小于 20% 判为共担；
- **话术生成**：只引用本次命中的真实条款，不编造法条与金额，输出三种语气（投诉 / 申诉 / 协商），
  正文统一为「事实 → 诉求 → 依据 → 证据」四段式。

证据缺口会单独列出（缺签收时间、缺开箱影像、主张假冒缺鉴定报告等）——判定「证据不足」
比给出一个没有依据的结论更负责。输出带免责声明：仅供争议处理参考，不构成法律意见。

### 3. 直播购物分身 —— 实时摘要与决策辅助

```
SubtitleSummarizer ─┬─▶ DanmakuSentiment   弹幕情感 / 热度 / 口碑标签
                    └─▶ PriceComparator    报价触发的全网比价
                              │
                              ▼
                            Merge          增量合并进会话快照
```

- **口播摘要**：正则 + 短语规则抽取「限量 500 件」「拍一发三」「前 100 名加赠」等信息，
  一句话只保留优先级最高的类型（价格 > 赠品 > 限量 > 时效 > 承诺 > 规格），避免同类噪音；
- **弹幕情感**：词典 + 频次统计，输出正向占比、情感分、每分钟热度与口碑标签，
  「太贵」「犹豫」这类词单独成为标签，不把少量样本夸大成结论；
- **一键比价**：识别到报价立即拉历史曲线，低于近 90 天均价 15% 时提示「值得冲」；
- **实时通道**：`WS /api/v1/live/sessions/{id}/ws`，客户端按批推送字幕与弹幕，服务端回推合并快照。

每批只处理增量、结果合并到快照，长直播不会因为累计数据而越跑越慢。

## RAG 知识增强

四类知识库：`brand_guide`（品牌规范）、`category_knowledge`（类目知识）、`case_study`（成功案例）、`compliance_rule`（合规规则）。

```
用户查询 → Embedding（BGE-large-zh 本地 / 千问云端双通道）
        → PGVector 相似度检索 → Top-K 分块
        → 注入 Agent 提示词上下文
```

可选增强（默认关闭，按需在 `.env` 开启）：

| 能力 | 开关 | 说明 |
|---|---|---|
| Query 改写 | `RAG_QUERY_REWRITING_ENABLED` | 多查询变体提升召回 |
| HyDE | `RAG_HYDE_ENABLED` | 假设文档嵌入 |
| 重排序 | `RAG_RERANKER_ENABLED` | BGE-reranker 交叉编码 |
| 混合检索 | `RAG_HYBRID_RETRIEVAL_ENABLED` | Dense + Sparse + ColBERT，RRF 融合 |
| Graph RAG | `GRAPH_RAG_ENABLED` | 实体/关系图谱 + 社区发现 |
| 记忆系统 | `MEMORY_ENABLED` | 经验沉淀、自动分类、遗忘机制 |

## Agent 可观测工作台

前端 `任务详情 → 工作台` 把一次运行完整摊开：

- **DAG 流程图**：每个 Agent 一个节点，实时显示等待 / 运行中 / 完成 / 失败；
- **概览**：耗时、Token 消耗、费用、上下游 Agent；
- **提示词**：完整的 System / Human Prompt，不截断，可复制；
- **输入输出**：该 Agent 接收的参数与产出的结构化结果；
- **子调用**：LLM / 工具调用明细。

支撑数据来自 `AgentLog`（`src/graph/state.py`）与 `agent_logs` 累加字段，经 WebSocket 推送。

## 安全与合规

**认证与租户隔离**
- API Token 走 SHA256 摘要存储，携带 Scope 权限；支持 `Authorization: Bearer` 与 `X-API-Key`；
- 所有业务查询强制带 `tenant_id`，跨租户访问返回 404；
- JWT 用于登录态，WebSocket 支持头鉴权（默认禁止 query 传 token）。

**平台合规**
- 广告法绝对化用语（“最佳”“第一”“100%”等）与平台敏感词检测；
- 主图白底、尺寸下限、图片数量上限、标题字数、搜索词字节数校验；
- 违规项分 `FAIL` / `WARNING` 两级，汇总到合规报告与适配器配置联动。

**凭证与上传**
- 适配器凭证以 Fernet 加密后存库（`CREDENTIALS_ENCRYPTION_KEY`）；
- 上传大小上限 `MAX_UPLOAD_SIZE_MB`，文件类型与 SHA256 去重。

## 降级矩阵

| 依赖 | 缺失/不可用时的行为 |
|---|---|
| LLM API Key | 文案与创意走规则模板，流程仍可完整跑通 |
| 图片厂商 | `ALLOW_MOCK_ASSETS=true` 时生成占位图并标记 `is_mock` |
| 视频厂商 | 同上，返回占位视频与进度状态 |
| PostgreSQL | 业务功能不可用（知识库、任务、资产均依赖），接口返回明确错误 |
| Redis | 任务状态退化为内存存储，重启后丢失 |
| 本地 Embedding 模型 | `RAG_ENABLED=false` 可跳过检索；未下载模型时 RAG 功能不可用 |
| OSS | `STORAGE_TYPE=local` 落本地 `./output`，经 `/static` 暴露 |
| 平台适配器 | 未注册的平台推送返回明确的 `push_failed` 与原因 |
| 比价数据源（ES / 采集服务） | 回退到模拟数据并标记 `is_mock=True`；`ALLOW_MOCK_SOURCES=false` 时明确报错而非编造价格 |
| 消费者侧开关 | `CONSUMER_FEATURES_ENABLED=false` 时 `/buyer`、`/dispute`、`/live` 统一返回 403 |

## 测试

```bash
# 全量测试（719 passed）
uv run pytest

# 指定目录
uv run pytest tests/test_models tests/test_agents
```

覆盖：模型契约、Agent 行为、工作流路由、刊登与合规、多租户隔离、WebSocket 鉴权、
RAG 检索与重排、知识图谱、存储后端、资产落库、买手决策卡、纠纷仲裁规则匹配、直播增量合并。

## 设计要点

**结构体传递而非自然语言**：Agent 之间传递 Pydantic 模型（`RequirementReport`、`CreativePlan`、
`Storyboard`、`QualityReport`），字段缺失在类型层暴露，不依赖上游措辞。

**状态累加语义**：`generated_images`、`agent_logs`、`quality_reports` 等列表字段用
`Annotated[list, add]` 声明 reducer，否则节点返回的 dict 会覆盖整个列表、丢失历史。

**降级即默认路径**：无 Key、无模型、无外部服务时都能跑，Mock 与规则回退不是补丁而是设计的一部分，
保证演示、验收与测试可复现。

**可观测先行**：每个 Agent 的执行都写 `AgentLog`（提示词、输入、输出、Token、费用），
前端不做二次加工即可还原完整决策链路。

**配置分层**：`Settings` 提供默认值 → `.env` 覆盖 → 数据库中的模型厂商配置优先，
三者优先级明确，便于多环境部署。

## 已知限制

- 本地 Embedding 首次运行需下载 BGE 模型（约 1.3GB），未就绪时 RAG 不可用但不影响其他功能；
- 视频生成依赖第三方异步接口，最长等待受厂商限制，超时按失败处理；
- eBay 适配器为 HTTP 模拟实现，接入真实交易 API 需替换签名与端点；
- 合规规则为规则表驱动，尚未接入 LLM 语义审核；
- 全网比价默认走模拟数据源，真实报价需部署 ES 价格索引或采集服务；
- 纠纷规则库覆盖 14 类常见场景，各平台细则差异较大，落地时需按目标平台补充；
- 直播分身以规则抽取为主，字幕依赖上游 ASR 提供分片，弹幕情感为词典判定而非语义模型；
- 本地存储适合单机，多实例部署应切换到 OSS 并保证 `/static` 由对象存储或 CDN 承载；
- 前端为单体 Vue 工程，构建产物经 Nginx 托管。

## 技术栈

| 层级 | 技术 |
|---|---|
| 工作流引擎 | LangChain 1.x、LangGraph 1.x |
| 后端框架 | FastAPI、Pydantic v2、SQLAlchemy 2.0（async） |
| 数据库 | PostgreSQL 16 + PGVector |
| 缓存/状态 | Redis 7 |
| Embedding | BGE-large-zh（本地）、千问 text-embedding（云端） |
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia + AntV G6 |
| 部署 | Docker Compose、Nginx |
| 包管理 | uv |

## License

本项目采用 [Apache License 2.0](LICENSE)。
