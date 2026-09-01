<div align="center">

# 🤖 多智能体跨境电商助手 (multi-agent-cross-border-assistant)

### 从商品分析到多平台刊登，多个 AI Agent 协作完成视觉内容生产——**你能实时看到每个 Agent 的思考与协作过程**

**基于 LangGraph 的多 Agent 协作 · 跨境电商智能融合 · 可观测 Agent 工作台**

[![GitHub Repo](https://img.shields.io/badge/GitHub-23372%2Fmulti-agent-cross-border-assistant-blue.svg?logo=github)](https://github.com/23372/multi-agent-cross-border-assistant)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4-42b883.svg?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-powered-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

</div>

> 💡 **一句话介绍**：**多智能体跨境电商助手 (MAA Platform)** 用一张 LangGraph 状态图编排 7+ 个专业 Agent，自动完成跨境电商的商品分析、AI 文案、图片/视频生成、合规检查、多平台刊登全流程；并通过一个 DevTools 风格的可观测工作台，让你实时看到每个 Agent 的提示词、传递参数与协作轨迹。
>
> 🌐 **GitHub 仓库**：[https://github.com/23372/multi-agent-cross-border-assistant](https://github.com/23372/multi-agent-cross-border-assistant)

---

## 📑 目录

- [✨ 这是什么](#-这是什么)
- [📸 效果展示](#-效果展示)
- [🚀 核心特性](#-核心特性)
- [🏗️ 系统架构](#-系统架构)
- [⚡ 快速开始](#-快速开始)
- [⚙️ 环境变量](#-环境变量)
- [📁 项目结构](#-项目结构)
- [🛠️ 技术栈](#-技术栈)
- [🧪 开发与测试](#-开发与测试)
- [🗺️ 路线图](#-路线图)
- [📄 许可证](#-许可证)

---

## ✨ 这是什么

多智能体跨境电商助手是一个面向跨境电商的 **多 Agent 协作系统**，利用 LangGraph 状态图驱动多个专业 Agent 协同工作，自动完成从商品分析到视觉内容生成、合规检查、多平台刊登的全流程。

- 📦 **商品信息分析** - Agent 自动提取卖点、分析竞品、识别目标人群
- ✍️ **AI 文案生成** - 多语言商品描述、平台风格适配、LLM 降级策略
- 🖼️ **图片生成** - 多模型支持，异步调用与回调模式
- 🎬 **视频生成** - 分镜设计 + 视频生成
- ✅ **合规检查** - 广告法禁词检测、平台规则验证
- 🌐 **多平台刊登** - 多平台适配器，凭证加密存储
- 📚 **RAG 知识增强** - PGVector 向量检索 + Graph RAG + CategoryMemory
- 📊 **AI 会话追踪** - Token 消耗统计、双币种费用预算、内容检索
- 🔬 **Agent 可观测工作台** - DAG 流程图 + 提示词轨迹 + 实时协作视图
- 🔌 **多模型厂商切换** - 支持多种 LLM/图片/视频厂商丝滑切换

> 💡 **适合谁？** 跨境电商从业者、AI 应用开发者、LangChain/LangGraph 学习者、对 Agent 可观测性感兴趣的研究者。

---

## 📸 效果展示

> 🎬 **Agent 可观测工作台**——这是平台最与众不同的部分。

**DAG 流程图视图**：每个 Agent 作为一个节点，实时显示执行状态（等待 / 运行中 / 完成 / 失败），节点间连线展示数据流向。

**DevTools 风格详情面板**：点击任意节点，右侧分 4 个 Tab 查看该 Agent 的完整工作过程：
- **概览** - 状态、耗时、Token 消耗、费用、上下游 Agent
- **提示词** - 完整的 System / Human Prompt（不截断，可一键复制）
- **输入输出** - 该 Agent 接收的参数与产出的结构化结果
- **子调用** - LLM / 工具调用的详细记录

**实时协作**：通过 WebSocket 推送，Agent 状态变化即时反映到流程图，无需刷新。

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Agent 工作台                            ● WS 已连接      │
│  任务 task_xxxx · 运行中 · 进度 ▓▓▓▓▓░░░░ 62%               │
├──────────────────────────────┬──────────────────────────────┤
│                              │ [概览] [提示词] [IO] [子调用] │
│        ┌──────────┐          │                              │
│        │ Orchestr │ ✅        │  Agent: CreativePlanner      │
│        └────┬─────┘          │  状态: ● 运行中 (脉冲)        │
│             │                 │  耗时: 3.2s · Token: 1,840   │
│        ┌────▼─────┐          │  费用: ¥0.018                │
│        │ ReqAnaly │ ✅        │                              │
│        └────┬─────┘          │  📥 上游: RequirementAnalyzer│
│             │                 │  📤 下游: VisualDesigner     │
│        ┌────▼─────┐          │                              │
│        │ Creative │ 🔄 运行中 │  System Prompt:             │
│        │ Planner  │ ●●●       │  你是一位资深跨境电商创意... │
│        └────┬─────┘          │  [完整展示 · 📋 复制]         │
│             │                 │                              │
│        ┌────▼─────┐          │                              │
│        │ VisualD  │ ⏳ 等待   │                              │
│        └──────────┘          │                              │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🚀 核心特性

| 特性 | 描述 |
|------|------|
| 🔬 **Agent 可观测工作台** | DAG 流程图（AntV G6）+ 提示词轨迹 + WebSocket 实时协作 |
| 🤖 **多 Agent 协作** | 7 个视觉生成 Agent + 4 个刊登 Agent + 3 个 RAG 增强 Agent + 3 个知识库 Agent |
| 🔄 **LangGraph 工作流** | 条件路由、并行执行、状态检查点、stream 模式实时回调、RAG 动态注入 |
| 🖼️ **图片生成** | 多模型支持，async_call + wait 模式 |
| 🎬 **视频生成** | HS256 JWT 鉴权 + 异步任务轮询 |
| 📚 **RAG 增强** | PGVector + BGE-large-zh / 云端 Embedding 双通道 |
| 🕸️ **Graph RAG** | 知识图谱实体/边 + CategoryMemory + 混合检索（RRF 融合） |
| ✅ **合规检查** | 广告法禁词检测 + 平台规则验证 |
| 🌐 **多平台刊登** | 多电商平台适配器 |
| 🔄 **多模型通道** | OpenAI 兼容协议 + 各厂商原生 SDK |
| 📊 **会话追踪** | Token 统计、双币种（USD/CNY）费用预算、内容搜索 |
| 🔐 **认证鉴权** | API Token（SHA256 + Scope 权限）+ 多租户隔离 |
| 🛡️ **优雅降级** | 无 API Key 时自动 Mock，LLM 降级链 |
| 🎨 **管理后台** | Vue 3 + Element Plus，15 个页面 |
| 🔌 **多厂商切换** | 模型厂商丝滑切换系统，支持 DB 驱动 + Settings 回退 |

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Vue 3 管理后台 (15 页面)                  │
│  仪表盘 │ 商品管理 │ 任务管理 │ 知识库 │ 刊登工具 │ AI 会话    │
│         │          │ 可观测工作台 │          │                │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API / WebSocket
┌──────────────────────────▼───────────────────────────────────┐
│                     FastAPI API 层 (40+ 端点)                 │
│  认证: API Token (SHA256 + Scope)    租户隔离: tenant_id      │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                   LangGraph 工作流引擎                         │
│                                                               │
│  视觉生成工作流:                                                │
│  Orchestrator -> ReqAnalyzer -> CreativePlanner -> VisualDesigner│
│       -> [ImageGen | VideoGen] -> QualityReviewer -> END          │
│                                                               │
│  刊登工作流:                                                    │
│  ImportProduct -> [AssetOptimizer | Copywriter] -> Compliance   │
│                                                               │
│  知识库 Agent 工作流:                                           │
│  QueryAnalyzer -> StrategyRouter -> HybridRetriever -> Fuser      │
└───────┬──────────────┬──────────────┬────────────────────────┘
        │              │              │
 ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼──────┐
 │   LLM 厂商   │ │  图片厂商  │ │  视频厂商   │
 │ (OpenAI兼容) │ │  (多模型)  │ │  (分镜设计)  │
 └──────┬──────┘ └─────┬─────┘ └─────┬──────┘
        │              │              │
 ┌──────▼──────────────▼──────────────▼────────┐
 │  PostgreSQL + PGVector  │  Redis  │  Storage │
 │  15+ 表 (向量/图谱/记忆)  │  缓存   │  本地/OSS │
 └─────────────────────────────────────────────┘
```

> 📊 更详细的类图与时序图见 [`docs/class-diagram.mermaid`](docs/class-diagram.mermaid) 与 [`docs/sequence-diagram.mermaid`](docs/sequence-diagram.mermaid)。

---

## ⚡ 快速开始

### 方式一：Windows 一键极简启动（面向学生 / 教学推荐 ⭐⭐⭐⭐⭐）

> 🎓 **专为课堂教学与零门槛体验设计**：无需手动敲击繁杂的命令行，双击即可一键拉起全套平台！

已在项目根目录下提供开箱即用的一键脚本：

| 脚本文件 | 说明 | 适用场景 |
|---------|------|---------|
| [**`一键启动.bat`**](一键启动.bat) | 自动检查环境，在独立窗口分别启动后端（`8002`）与前端（`5173`），并**自动在浏览器中弹出平台首页** | **日常上课 / 实验（最常用）** |
| [**`一键停止.bat`**](一键停止.bat) | 自动扫描并释放 `8002` 与 `5173` 端口占用，干净退出 | 结束实验或出现端口冲突时 |
| [**`一键初始化环境.bat`**](一键初始化环境.bat) | 自动创建 Conda `cbcf` 虚拟环境、配置清华源并安装 Python 和 npm 所有依赖 | 新学生 / 新电脑首次配置 |
| [**`学生快速上手指南.md`**](学生快速上手指南.md) | 极简图文指引与常见问题速查 | 直接分发给学生阅读 |

```
使用极简步骤：
1.（仅新电脑首次）双击【一键初始化环境.bat】
2. 双击【一键启动.bat】 -> 浏览器自动弹出 http://localhost:5173/ 即可使用！
3. 使用完毕后双击【一键停止.bat】退出
```

---

### 方式二：Docker 一键部署

> 🖥️ **目标电脑只需安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)**，一条命令即可把整套平台（后端 + 前端 + PostgreSQL + Redis）跑起来。

```bash
# 1. 进入项目目录
cd multi-agent-cross-border-assistant

# 2.（首次）准备环境变量文件，按需填入 API Key
#    不填也能跑：Mock 模式会自动降级生成占位资产
cp .env.example .env

# 3. 一键构建并启动（含 PostgreSQL 16 + pgvector + Redis）
docker compose up -d --build

# 4. 访问
#   前端:          http://localhost:3000
#   后端 API 文档:  http://localhost:8000/docs
#   后端健康检查:   http://localhost:8000/api/v1/health
```

> ⏳ **首次启动说明**：
> - 首次启动会自动下载本地 Embedding 模型（`BAAI/bge-large-zh`，约 **1.3GB**，走 hf-mirror 镜像站），期间 RAG 检索功能暂不可用，其余功能正常；下载失败会自动降级启动，不影响演示。
> - 后端镜像因内置 `sentence-transformers`（含 PyTorch），体积约 **4–5GB**，首次构建较慢，属正常现象。
> - 模型与数据库均持久化在 `./models` 卷与 `pgdata`/`redis_data` 卷中，二次启动无需重新下载。

<details>
<summary>共享模式（使用已有 PostgreSQL + Redis，如 ait-share-docker）</summary>

```bash
# 首次使用需手动启用 pgvector 扩展
docker exec <postgres容器名> psql -U postgres -d cbcf -c "CREATE EXTENSION IF NOT EXISTS vector;"

docker compose -f docker-compose.shared.yml up -d --build
```
</details>

### 方式三：本地手动开发（Conda 命令行模式）

```bash
# 0. 前置条件：启动共享 Docker 容器（PostgreSQL + Redis）
#    如未启动，请先启动或使用 docker-compose.yml 独立部署
docker start shared-postgres shared-redis 2>/dev/null || echo "请先启动 Docker 容器"

# 0.1 首次使用需启用 pgvector 扩展
docker exec shared-postgres psql -U postgres -d cbcf -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 1. 创建并激活 conda 虚拟环境
conda create -n cbcf python=3.13 -y
conda activate cbcf

# 2. 进入项目目录，安装后端依赖
cd multi-agent-cross-border-assistant
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，至少配置 POSTGRES_PASSWORD 和 REDIS_URL
# （或直接使用现有 .env，已预配置连接本地 shared-postgres/shared-redis）

# 4. 启动后端 (默认端口 8002)
python main.py

# 5. 新开终端，启动前端 (默认端口 5174)
cd frontend
npm install
npm run dev

# 6. 访问
#   前端管理后台:  http://localhost:5174
#   后端 API 文档: http://localhost:8002/docs
#   后端健康检查:  http://localhost:8002/api/v1/health
```

> 🛡️ **Mock 模式**：`.env` 已默认配置 `ALLOW_MOCK_ASSETS=true`（无 API Key 时自动降级为 Mock 资产）。需要 PostgreSQL 和 Redis 支持数据持久化和 RAG 知识库功能。如仅需体验 Mock 资产生成，可设 `RAG_ENABLED=false`。

---

## ⚙️ 环境变量

### 必填（Mock 模式下可不填）

| 变量 | 说明 |
|------|------|
| `QWEN_API_KEY` | LLM API Key（支持 OpenAI 兼容协议） |

### 核心可选

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `dashscope` | LLM 提供商 |
| `QWEN_API_BASE` | - | LLM OpenAI 兼容端点 |
| `DASHSCOPE_API_KEY` | - | 图片生成 API Key |
| `KLING_ACCESS_KEY` | - | 视频生成 Access Key |
| `KLING_SECRET_KEY` | - | 视频生成 Secret Key |
| `EMBEDDING_PROVIDER` | `local` | Embedding 提供商 |
| `EMBEDDING_MODEL` | `BAAI/bge-large-zh` | 本地 Embedding 模型名称 |
| `RAG_ENABLED` | `true` | 启用 RAG 知识检索 |
| `RETRIEVAL_TOP_K` | `5` | 检索返回数量 |
| `SIMILARITY_THRESHOLD` | `0.7` | 相似度阈值 |
| `POSTGRES_HOST` | `localhost` | PostgreSQL 主机 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_USER` | `postgres` | PostgreSQL 用户名 |
| `POSTGRES_PASSWORD` | - | PostgreSQL 密码 |
| `POSTGRES_DB` | `cbcf` | PostgreSQL 数据库名 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 URL |
| `STORAGE_TYPE` | `local` | 存储类型：`local` 或 `oss` |
| `ALLOW_MOCK_ASSETS` | `true` | 无 API Key 时允许 Mock 降级 |

完整配置见 [`.env.example`](.env.example)。

---

## 📁 项目结构

```
multi-agent-cross-border-assistant/
├── src/                          # 后端源码
│   ├── agents/                   # Agent 实现
│   │   ├── orchestrator.py       #   编排调度 Agent
│   │   ├── requirement_analyzer.py  # 需求分析 Agent
│   │   ├── creative_planner.py   #   创意策划 Agent
│   │   ├── visual_designer.py    #   视觉设计 Agent
│   │   ├── image_generator.py    #   图片生成 Agent
│   │   ├── video_generator.py    #   视频生成 Agent
│   │   ├── quality_reviewer.py   #   质量审核 Agent
│   │   ├── rag_*.py              #   RAG 增强 Agent (3个)
│   │   └── listing_*.py          #   刊登 Agent (5个)
│   ├── graph/                    # LangGraph 状态图与工作流
│   │   ├── workflow.py           #   视觉生成工作流
│   │   └── listing_workflow.py   #   刊登工作流
│   ├── api/                      # FastAPI 路由 + Schema + Service
│   │   ├── router/               #   路由模块 (12个)
│   │   ├── schema/               #   请求/响应模型
│   │   └── service/              #   业务服务
│   ├── clients/                  # 外部服务客户端
│   ├── rag/                      # RAG 检索管道
│   │   ├── retriever.py          #   知识检索器
│   │   ├── embeddings.py         #   双通道 Embedding
│   │   └── graph_memory.py       #   Graph RAG 记忆
│   ├── knowledge/                # 知识图谱 + 混合检索
│   │   ├── hybrid_retriever.py   #   RRF 融合检索
│   │   └── agent_workflow.py     #   知识库 Agent 工作流
│   ├── config/                   # 配置管理 (pydantic-settings)
│   ├── db/                       # 数据库 (15+ 表)
│   ├── auth/                     # API Token 认证 + 多租户
│   ├── models/                   # Pydantic 数据模型
│   └── storage/                  # 文件存储 (本地/OSS)
├── frontend/                     # Vue 3 前端
│   └── src/
│       ├── views/                # 页面组件 (15个)
│       ├── components/workbench/ #   Agent 可观测工作台组件
│       ├── api/                  # API 调用层
│       ├── types/                # TypeScript 类型
│       ├── stores/               # Pinia 状态管理
│       └── styles/               # 全局样式 (CSS 变量设计系统)
├── tests/                        # 测试用例
├── docs/                         # 设计文档与图表
├── docker-compose.yml            # Docker 编排
├── Dockerfile                    # 后端镜像
├── Dockerfile.frontend           # 前端镜像
└── pyproject.toml                # 项目配置
```

---

## 🛠️ 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **工作流引擎** | LangChain, LangGraph | langchain==1.3.14, langgraph==1.2.10 |
| **后端框架** | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) | pydantic==2.13.4, pydantic-settings==2.14.2 |
| **语言模型** | OpenAI 兼容协议 + 多厂商 SDK | langchain-openai==1.4.1 |
| **图片生成** | 多模型支持（异步调用 + 回调模式） | — |
| **视频生成** | 多模型支持（JWT 鉴权 + 任务轮询） | — |
| **向量检索** | PGVector, BGE-large-zh（本地 Embedding） | sentence-transformers>=2.2.0 |
| **图谱检索** | Graph RAG (实体/关系/社区/摘要) | python-igraph>=0.11.0 |
| **前端框架** | Vue 3, TypeScript, Element Plus, Pinia, AntV G6 | — |
| **数据库** | PostgreSQL 16 + PGVector, Redis 6 | — |
| **存储** | 本地文件系统 / 云存储 OSS | — |
| **部署** | Docker Compose, Nginx | — |

---

## 🧪 开发与测试

```bash
# 运行测试
python -m pytest

# 带覆盖率报告
python -m pytest --cov=src --cov-report=html

# 代码格式化
ruff format .

# Lint 检查
ruff check .

# 类型检查
mypy src/
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 🗺️ 路线图

- [x] **v0.1.0** - LangGraph 7-Agent 视觉生成工作流 + RAG 知识库 + 合规检查 + Vue 3 管理后台
- [x] **v0.2.0** - 多模型厂商对接 + AI 会话追踪 + Agent 可观测工作台（DAG + 提示词轨迹）
- [ ] **v0.3.0** - 高级 RAG（HyDE / 多查询重写）+ GraphRAG 增强 + 生产级刊登 + 图片 RAG
- [ ] **v0.4.0** - Agent 自适应重试与自愈 + 工作流可视化编辑器
- [ ] **v1.0.0** - 多租户 SaaS 化 + 插件式 Agent 市场 + 全面生产就绪

---

## 📄 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。

---

<div align="center">

**多智能体跨境电商助手** — 让 AI Agent 协作改变跨境电商内容生产方式

</div>
