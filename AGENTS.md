# AGENTS.md - 项目架构文档

> **项目名称**: 多智能体电商购物助手
> **版本**: 0.2.0
> **最后更新**: 2026-11-09

---

## 一、项目概述

### 1.1 项目定位

基于 LangChain/LangGraph 构建的**多智能体电商购物助手**，同时覆盖**商家侧**与**消费者侧**：

- **商家侧**：多个专业 Agent 协同工作，实现商品营销图片和视频的自动化生成、合规检查与多平台刊登；
- **消费者侧**：10 个 Agent 组成「虚拟买手团」（协同选品与比价）、「售后纠纷仲裁庭」（证据链与话术）、
  「直播购物分身」（实时摘要与决策辅助）。

两侧共用同一个 FastAPI 服务、同一套多租户隔离与同一套可观测体系。

### 1.2 核心能力

| 能力 | 描述 |
|------|------|
| 🤖 多 Agent 协作 | 商家侧 7 个专业 Agent 协同工作，分工明确 |
| 🖼️ 智能图片生成 | 主图、场景图、卖点图自动生成 |
| 🎬 视频分镜生成 | 智能分镜设计 + 视频合成 |
| 🎨 创意自动策划 | 风格推荐、配色方案设计 |
| ✅ 质量自动审核 | 内容质量检测、合规审核 |
| 📚 RAG 知识增强 | 企业知识库检索增强，提升生成质量 |
| 🛒 虚拟买手团 | 风格顾问 / 性价比分析师 / 质检员三路并行，合成买手决策卡 |
| ⚖️ 纠纷仲裁庭 | 事实还原 + 规则库匹配（附法条）+ 三套维权话术 |
| 📺 直播购物分身 | 口播关键信息抽取 + 弹幕口碑 + 报价触发一键比价 |

### 1.3 技术栈

| 层级 | 技术选型 |
|------|----------|
| **语言** | Python 3.11+ |
| **LLM 框架** | LangChain 0.3+, LangGraph 0.2+ |
| **主力 LLM** | 阿里云通义千问 (qwen3.5-flash) |
| **图像生成** | 阿里云通义万象 (wanx-v1) |
| **视频生成** | 可灵 AI (kling-v1) |
| **向量数据库** | PostgreSQL + PGVector |
| **Embedding** | BGE-large-zh (本地部署) |
| **API 框架** | FastAPI |
| **前端框架** | Vue 3 + TypeScript + Element Plus |
| **存储** | PostgreSQL (向量/关系数据) + Redis (任务状态) + 本地/OSS (资源文件) |
| **包管理** | uv |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3 + TS)                        │
│                    商品录入 | 任务管理 | 结果展示                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                             │
│              /api/v1/products | /api/v1/tasks | /health              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow Engine                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Agent 协作流程                              │   │
│  │                                                               │   │
│  │   Orchestrator ──▶ RequirementAnalyzer ──▶ CreativePlanner   │   │
│  │         │                                              │      │   │
│  │         │                                              ▼      │   │
│  │         │         ◀────────────────── VisualDesigner       │   │
│  │         │                    │                    │         │   │
│  │         │                    ▼                    ▼         │   │
│  │         │           ImageGenerator    ◀──▶  VideoGenerator  │   │
│  │         │                    │                    │         │   │
│  │         └────────────────────┴────────────────────┘         │   │
│  │                              │                               │   │
│  │                              ▼                               │   │
│  │                      QualityReviewer                         │   │
│  │                              │                               │   │
│  │                              ▼                               │   │
│  │                         [END]                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      External Services                               │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│   │ DashScope   │  │  可灵 AI    │  │   Redis     │                │
│   │ (LLM/Image) │  │  (Video)    │  │  (State)    │                │
│   └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流向

```
Product (商品信息)
    │
    ▼
GenerationRequest (生成请求)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   AgentState (状态流转)                   │
│                                                          │
│  product_info → requirement_report → creative_plan      │
│       → generation_prompts → generated_images/video     │
│       → quality_reports → final_results                  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
AssetCollection (最终产出)
```

---

## 三、模块结构

### 3.1 目录结构

```
multi-agent-ecommerce-shopping-assistant/
├── main.py                 # FastAPI 应用入口
├── run_workflow.py         # CLI 工作流运行脚本
├── pyproject.toml          # 项目配置 (依赖、工具配置)
├── uv.lock                 # 依赖锁定文件
│
├── src/                    # 后端源码
│   ├── agents/             # Agent 实现（25 个：视觉 7 + RAG 4 + 刊登 4 + 消费者侧 10）
│   │   ├── base.py         # Agent 基类
│   │   ├── orchestrator.py # 编排调度 Agent
│   │   ├── requirement_analyzer.py  # 需求分析 Agent
│   │   ├── creative_planner.py      # 创意策划 Agent
│   │   ├── visual_designer.py       # 视觉设计 Agent
│   │   ├── image_generator.py       # 图片生成 Agent
│   │   ├── video_generator.py       # 视频生成 Agent
│   │   ├── quality_reviewer.py      # 质量审核 Agent
│   │   ├── rag_*.py                 # RAG 增强版 Agent
│   │   ├── listing_*.py             # 刊登链路 Agent
│   │   ├── consumer_base.py         # 消费者侧基类（LLM 可选）
│   │   ├── buyer_style_advisor.py   # 风格顾问
│   │   ├── buyer_value_analyst.py   # 性价比分析师
│   │   ├── buyer_quality_inspector.py  # 质检员
│   │   ├── buyer_decision_maker.py  # 决策官
│   │   ├── buyer_review_lexicon.py  # 差评词库 + 类目退货率基准
│   │   ├── price_analysis.py        # 比价聚合（买手团与直播共用）
│   │   ├── dispute_fact_restorer.py # 事实还原
│   │   ├── dispute_rule_interpreter.py  # 规则解读
│   │   ├── dispute_negotiator.py    # 话术生成
│   │   ├── dispute_rules.py         # 平台争议规则库
│   │   ├── live_subtitle_summarizer.py  # 口播摘要
│   │   ├── live_danmaku_sentiment.py    # 弹幕情感
│   │   ├── live_price_comparator.py     # 一键比价
│   │   └── live_lexicon.py          # 口播关键词与弹幕词典
│   │
│   ├── graph/              # LangGraph 状态图
│   │   ├── state.py        # AgentState 定义
│   │   ├── workflow.py     # 视觉生成工作流
│   │   ├── listing_state.py / listing_workflow.py    # 刊登
│   │   ├── buyer_state.py / buyer_workflow.py        # 买手团（三路并行）
│   │   ├── dispute_state.py / dispute_workflow.py    # 仲裁庭（三段串行）
│   │   └── live_state.py / live_workflow.py          # 直播分身（增量合并）
│   │
│   ├── models/             # 数据模型
│   │   ├── product.py      # 商品信息模型
│   │   ├── creative.py     # 创意方案模型
│   │   ├── storyboard.py   # 分镜脚本模型
│   │   ├── assets.py       # 生成资产模型
│   │   ├── listing.py      # 刊登模型
│   │   ├── buyer.py        # 买手决策卡 / 比价 / 风格画像
│   │   ├── dispute.py      # 仲裁案件 / 裁决 / 话术
│   │   └── live.py         # 直播快照 / 关键信息 / 弹幕情感
│   │
│   ├── api/                # API 层
│   │   ├── router/         # 路由定义（17 个模块，含 buyer/dispute/live）
│   │   ├── schema/         # 请求/响应模型
│   │   └── service/        # 服务层
│   │       ├── redis_client.py    # Redis 客户端
│   │       └── task_manager.py    # 任务管理器
│   │
│   ├── db/                 # 数据库模块
│   │   ├── postgres.py     # PostgreSQL 连接管理
│   │   ├── models.py       # 知识库 / 商品 / 任务模型
│   │   ├── listing_models.py    # 刊登模型
│   │   ├── consumer_models.py   # 消费者侧三张表
│   │   └── vector_store.py # 向量存储接口
│   │
│   ├── clients/            # 外部厂商客户端
│   │   ├── price_search.py # 全网比价数据源（ES / 采集服务 / 模拟）
│   │   └── ...             # LLM / 图片 / 视频厂商
│   │
│   ├── rag/                # RAG 检索增强模块
│   │   ├── __init__.py     # 模块导出
│   │   ├── embeddings.py   # BGE Embedding 封装
│   │   ├── retriever.py    # 知识检索器
│   │   ├── chunker.py      # 语义分块
│   │   ├── document_processor.py  # 文档处理
│   │   └── logger.py       # RAG 日志服务
│   │
│   ├── config/             # 配置管理
│   │   └── settings.py     # Settings 配置类
│   │
│   └── tools/              # 工具集成 (预留)
│
├── frontend/               # 前端源码
│   ├── src/
│   │   ├── api/            # API 调用封装
│   │   ├── components/     # Vue 组件
│   │   ├── views/          # 页面视图
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── router/         # Vue Router 路由
│   │   └── types/          # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                  # 测试用例
│   ├── test_agents/        # Agent 测试
│   ├── test_graph/         # 工作流测试
│   ├── test_models/        # 模型测试
│   └── test_tools/         # 工具测试
│
└── documents/              # 开发文档
    ├── 多智能体电商购物助手开发计划_2026-09-02.md
    └── 操作文档.md
```

### 3.2 核心模块说明

#### 3.2.1 Agent 模块 (`src/agents/`)

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `OrchestratorAgent` | 编排调度，初始化工作流 | Product, GenerationRequest | 初始化状态 |
| `RequirementAnalyzerAgent` | 分析商品信息，提取卖点 | Product | RequirementReport |
| `CreativePlannerAgent` | 生成创意方案和配色 | RequirementReport | CreativePlan, ColorPalette |
| `VisualDesignerAgent` | 设计图片提示词和分镜 | CreativePlan | ImagePrompts, Storyboard |
| `ImageGeneratorAgent` | 调用图像生成 API | ImagePrompts | GeneratedImage[] |
| `VideoGeneratorAgent` | 调用视频生成 API | Storyboard | GeneratedVideo |
| `QualityReviewerAgent` | 审核生成质量 | GeneratedAssets | QualityReport |

#### 3.2.2 状态图模块 (`src/graph/`)

**AgentState 核心字段**:

```python
class AgentState(BaseModel):
    # 输入
    product_info: Product | None
    generation_request: GenerationRequest | None

    # 分析阶段
    requirement_report: RequirementReport | None
    selling_points: list[dict]  # 累加字段

    # 创意阶段
    creative_plan: CreativePlan | None
    color_palette: dict | None

    # 设计阶段
    generation_prompts: list[dict]  # 累加字段

    # 生成阶段
    generated_images: list[GeneratedImage]  # 累加字段
    storyboard: Storyboard | None
    generated_video: GeneratedVideo | None

    # 审核阶段
    quality_reports: list[QualityReport]  # 累加字段
    quality_score: float | None
    issues: list[dict]  # 累加字段

    # 输出
    asset_collection: AssetCollection | None
    final_results: dict | None

    # 元数据
    current_step: str
    completed_steps: list[str]
    agent_logs: list[AgentLog]  # 累加字段
```

#### 3.2.3 数据模型 (`src/models/`)

```
Product (商品信息)
    ├── ProductCategory (类目枚举)
    ├── SellingPoint (卖点)
    │   └── SellingPointType (卖点类型)
    └── ProductSpec (规格)

CreativePlan (创意方案)
    ├── theme (主题)
    ├── style (风格)
    ├── color_scheme (配色)
    └── visual_elements (视觉元素)

Storyboard (分镜脚本)
    └── StoryboardScene[] (分镜场景)
        ├── duration (时长)
        ├── description (描述)
        └── visual_prompt (视觉提示)

GeneratedImage (生成图片)
    ├── image_type (类型: main/scene/selling_point)
    ├── url (图片地址)
    └── metadata (元数据)

GeneratedVideo (生成视频)
    ├── title (标题)
    ├── url (视频地址)
    └── duration (时长)

QualityReport (质量报告)
    ├── score (评分)
    ├── issues (问题列表)
    └── suggestions (改进建议)
```

#### 3.2.4 RAG 模块 (`src/rag/`)

**知识库类型**:

| 文档类型 | 说明 | 用途 |
|----------|------|------|
| `brand_guide` | 品牌规范 | 品牌调性、视觉规范、语言风格 |
| `category_knowledge` | 类目知识 | 商品特点、卖点模板、关键词 |
| `case_study` | 成功案例 | 历史优秀创意方案参考 |
| `compliance_rule` | 合规规则 | 广告法禁止词、平台审核标准 |

**RAG 增强 Agent**:

| Agent | 增强能力 |
|-------|----------|
| `RAGEnhancedRequirementAnalyzer` | 检索品牌规范、类目知识辅助商品分析 |
| `RAGEnhancedCreativePlanner` | 获取品牌视觉规范、类目风格参考 |
| `RAGEnhancedQualityReviewer` | 加载合规规则进行内容审核 |

**检索流程**:

```
用户查询 → Embedding (BGE-large-zh)
    → PGVector 相似度搜索
    → 返回 Top-K 相关文档分块
    → 注入 Agent Prompt 上下文
```

**AgentState RAG 字段**:

```python
class AgentState(BaseModel):
    # RAG 增强字段
    rag_sources: list[dict]  # 检索来源列表（累加）
    rag_context: str | None   # 检索上下文
    rag_enabled: bool         # 是否启用 RAG
```

#### 3.2.5 消费者侧模块 (`src/agents/buyer_* | dispute_* | live_*`)

三组 Agent 共用 `ConsumerAgentBase`：规则为主干、LLM 只做表述增强，缺 API Key 时自动降级为规则结果。

**虚拟买手团**

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `StyleAdvisorAgent` | 行为权重(1/2/3/4)统计风格与价格带，计算匹配分 | BrowsingRecord[] | StyleProfile, style_fit |
| `ValueAnalystAgent` | 调用比价数据源，聚合全网报价与历史曲线 | CandidateProduct | PriceComparison |
| `QualityInspectorAgent` | 差评词库挖掘 + 退货率基准对比 | CandidateProduct.reviews | QualityAssessment |
| `DecisionMakerAgent` | 加权评分 + 风险惩罚 + 理由/预警合成 | 三路结论 | BuyerDecisionCard |

**售后纠纷仲裁庭**

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `FactRestorerAgent` | 证据归一化、时间线、事实标记、证据缺口 | 聊天/物流/开箱 | FactSheet, facts |
| `RuleInterpreterAgent` | 规则库匹配 + 责任聚合 + 赔付建议 + 时效提示 | facts, 上下文 | ArbitrationVerdict |
| `NegotiatorAgent` | 三语气话术，仅引用命中条款 | FactSheet, verdict | ComplaintDraft[] |

**直播购物分身**

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `SubtitleSummarizerAgent` | 口播关键信息抽取（价格/限量/赠品/时效/承诺/规格） | TranscriptSegment[] | LiveKeyPoint[] |
| `DanmakuSentimentAgent` | 弹幕情感、热度、口碑标签 | DanmakuItem[] | SentimentBreakdown |
| `PriceComparatorAgent` | 报价触发全网比价 | LiveKeyPoint[] | LivePriceAlert |

**规则底座模块**

| 模块 | 内容 |
|------|------|
| `buyer_review_lexicon.py` | 60+ 差评关键词 → 缺陷类别 + 严重度；类目退货率基准；贝叶斯平滑参数 |
| `dispute_rules.py` | 14 条争议规则（事实条件 + 法条摘要 + 倾向方），`match_rules` / `aggregate_responsibility` |
| `live_lexicon.py` | 价格正则、六类关键信息关键词、弹幕正负向词典与否定前缀 |
| `price_analysis.py` | 比价聚合、`PriceVerdict` 判定、性价比折算（三处共用同一口径） |

**数据源与降级**

| 数据源 | 优先级 | 缺省行为 |
|--------|--------|----------|
| `EsPriceSearchBackend` | 1 | 需 `ELASTICSEARCH_URL`；读 `product_prices` 索引 |
| `CrawlerPriceSearchBackend` | 2 | 需 `PRICE_CRAWLER_ENDPOINT`；本项目只定义契约 |
| `MockPriceSearchBackend` | 3 | 确定性模拟，`is_mock=True`，决策卡与比价提醒显式标注 |

`ALLOW_MOCK_SOURCES=false` 且前两者未配置时，比价返回「数据源不可用」，不伪造价格。

**持久化表**（`src/db/consumer_models.py`）

| 表 | 关键列 | 说明 |
|----|--------|------|
| `buyer_decision_cards` | tenant_id, user_id, card_id, overall_score, recommendation, payload | 决策卡全量 JSON |
| `dispute_cases` | tenant_id, case_id, order_id, responsibility, confidence, payload | 案件全量 JSON |
| `live_sessions` | tenant_id, session_id, room_id, status, payload, ended_at | 最新快照 JSON |

---

## 四、工作流设计

### 4.1 状态图流程

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Orchestrator│ ←── 初始化工作流
└──────┬──────┘
       │ (条件路由: 有错误则 END)
       ▼
┌─────────────┐
│ Requirement │ ←── 分析商品信息
│  Analyzer   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Creative   │ ←── 生成创意方案
│  Planner    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Visual    │ ←── 设计提示词/分镜
│  Designer   │
└──────┬──────┘
       │ (条件路由: 根据任务类型)
       ▼
┌──────┴──────┐
│             │
▼             ▼
┌─────────┐ ┌─────────┐
│  Image  │ │  Video  │
│Generator│ │Generator│
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
    ┌─────────────┐
    │   Quality   │ ←── 质量审核
    │  Reviewer   │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │    END      │
    └─────────────┘
```

### 4.2 任务类型路由

| 任务类型 | 路由路径 |
|----------|----------|
| `image_only` | VisualDesigner → ImageGenerator → QualityReviewer |
| `video_only` | VisualDesigner → VideoGenerator → QualityReviewer |
| `image_and_video` | VisualDesigner → ImageGenerator → VideoGenerator → QualityReviewer |

### 4.3 状态累加机制

LangGraph 使用 `Annotated` 实现字段累加：

```python
from operator import add
from typing import Annotated

class AgentState(BaseModel):
    # 累加字段：新值会追加到列表而非覆盖
    generated_images: Annotated[list[GeneratedImage], add] = Field(default_factory=list)
    agent_logs: Annotated[list[AgentLog], add] = Field(default_factory=list)
```

---

## 五、API 设计

### 5.1 端点列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 欢迎信息 |
| `/health` | GET | 健康检查 |
| `/api/v1/products` | POST | 创建商品 |
| `/api/v1/products/{id}` | GET | 获取商品详情 |
| `/api/v1/tasks` | POST | 创建生成任务 |
| `/api/v1/tasks/{id}` | GET | 获取任务状态 |
| `/api/v1/tasks/{id}/cancel` | POST | 取消任务 |
| `/api/v1/buyer/decisions` | POST/GET | 生成决策卡 / 历史列表 |
| `/api/v1/buyer/decisions/{card_id}` | GET | 决策卡详情 |
| `/api/v1/buyer/compare` | POST | 全网比价 |
| `/api/v1/dispute/cases` | POST/GET | 提交仲裁 / 案件列表 |
| `/api/v1/dispute/cases/{case_id}` | GET | 案件详情 |
| `/api/v1/dispute/cases/{case_id}/draft` | POST | 重生成指定语气话术 |
| `/api/v1/live/sessions` | POST/GET | 创建直播会话 / 会话列表 |
| `/api/v1/live/sessions/{id}/ingest` | POST | 推入字幕与弹幕 |
| `/api/v1/live/sessions/{id}/snapshot` | GET | 最新快照 |
| `/api/v1/live/sessions/{id}/end` | POST | 结束会话 |
| `/api/v1/live/sessions/{id}/ws` | WS | 直播快照实时推送 |
| `/api/v1/live/price-check` | POST | 一键比价 |

### 5.2 请求示例

**创建生成任务**:

```json
POST /api/v1/tasks
{
  "product_id": "prod_001",
  "task_type": "image_and_video",
  "image_types": ["main", "scene", "selling_point"],
  "image_count_per_type": 1,
  "video_duration": 30.0,
  "style_preference": "科技感、现代简约"
}
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "task_id": "task_xxx",
    "status": "pending",
    "created_at": "2026-09-08T10:00:00Z"
  }
}
```

---

## 六、配置管理

### 6.1 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | 必填 |
| `KLING_ACCESS_KEY` | 可灵 AI Access Key | 必填 |
| `KLING_SECRET_KEY` | 可灵 AI Secret Key | 必填 |
| `REDIS_URL` | Redis 连接 URL | `redis://localhost:6379/0` |
| `STORAGE_TYPE` | 存储类型 | `local` |
| `STORAGE_PATH` | 本地存储路径 | `./output` |
| `LLM_MODEL` | LLM 模型名称 | `qwen3.5-flash` |
| `IMAGE_MODEL` | 图像生成模型 | `wanx-v1` |
| `VIDEO_MODEL` | 视频生成模型 | `kling-v1` |
| `CONSUMER_FEATURES_ENABLED` | 启用消费者侧三套能力 | `true` |
| `PRICE_SEARCH_BACKEND` | 比价数据源：auto/es/crawler/mock | `auto` |
| `ELASTICSEARCH_URL` | ES 地址，配置后 auto 优先走 ES | 空 |
| `PRICE_CRAWLER_ENDPOINT` | 独立采集服务地址 | 空 |
| `ALLOW_MOCK_SOURCES` | 允许降级为模拟比价数据 | `true` |
| `BUYER_WEIGHT_STYLE/VALUE/QUALITY` | 决策卡三项权重（自动归一化） | 0.3 / 0.4 / 0.3 |
| `LIVE_DANMAKU_WINDOW_SECONDS` | 弹幕情感统计窗口 | `120` |

### 6.2 配置类

```python
from src.config.settings import get_settings

settings = get_settings()
api_key = settings.dashscope_api_key
```

---

## 七、开发规范

### 7.1 代码风格

- 遵循 PEP 8，使用 `ruff format` 格式化
- 所有公共函数必须有类型注解
- 使用 Google 风格 docstring
- 行长度最大 100 字符

### 7.2 测试规范

- 使用 pytest + pytest-asyncio
- 代码覆盖率要求 ≥ 80%
- Mock LLM 调用避免真实 API 请求

```bash
# 运行测试
uv run pytest

# 带覆盖率报告
uv run pytest --cov=src --cov-report=html
```

### 7.3 提交规范

- feat: 新功能
- fix: Bug 修复
- docs: 文档更新
- refactor: 代码重构
- test: 测试相关

---

## 八、扩展指南

### 8.1 添加新 Agent

1. 在 `src/agents/` 创建新的 Agent 类，继承 `BaseAgent[AgentState]`
2. 实现 `execute(state: AgentState) -> AgentResult` 方法
3. 在 `src/graph/workflow.py` 中注册节点和边

```python
# src/agents/my_agent.py
class MyAgent(BaseAgent[AgentState]):
    def __init__(self):
        super().__init__(role=AgentRole.MY_ROLE)

    async def execute(self, state: AgentState) -> AgentResult:
        # 实现逻辑
        return AgentResult(success=True, data={...})
```

### 8.2 添加新模型

1. 在 `src/models/` 创建 Pydantic 模型
2. 在 `src/graph/state.py` 的 `AgentState` 中添加字段

### 8.3 添加新 API

1. 在 `src/api/schema/` 定义请求/响应模型
2. 在 `src/api/router/` 创建路由
3. 在 `src/api/router/__init__.py` 注册路由

---

## 九、依赖关系

### 9.1 核心依赖

```toml
[project]
dependencies = [
    "langchain>=0.3.0",
    "langchain-community>=0.3.0",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "dashscope>=1.14.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "httpx>=0.25.0",
    "redis>=5.0.0",
]
```

### 9.2 开发依赖

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
]
```

---

## 十、部署说明

### 10.1 本地开发

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env

# 启动 API 服务
uv run python main.py

# 或运行示例工作流
uv run python run_workflow.py
```

### 10.2 生产部署

```bash
# 构建
uv build

# 启动 Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## 十一、参考资源

- [LangChain 文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [通义千问 API](https://help.aliyun.com/zh/dashscope/)
- [可灵 AI API](https://platform.klingai.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [uv 文档](https://docs.astral.sh/uv/)