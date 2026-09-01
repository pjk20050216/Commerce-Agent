"""Seed demo conversation data for AI 会话记录 page."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

# Demo conversations simulating real AI agent usage
DEMO_CONVERSATIONS = [
    {
        "agent_name": "RequirementAnalyzer",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "分析商品：无线蓝牙耳机 Pro Max，目标市场美国，客单价$49.99，主推卖点：主动降噪、40小时续航、IPX5防水",
        "output_content": "需求分析完成。核心卖点：1) 主动降噪（ANC）技术领先；2) 超长续航40小时（行业平均水平25-30h）；3) IPX5防水适合运动场景。建议定位：中端运动降噪耳机，对标Jabra Elite系列。目标人群：25-40岁通勤+运动人群。",
        "input_tokens": 156, "output_tokens": 210, "total_tokens": 366,
        "cost_cny": 0.002, "latency_ms": 1240, "status": "success",
    },
    {
        "agent_name": "CreativePlanner",
        "model_name": "qwen-max",
        "provider": "qwen",
        "input_content": "基于需求分析结果，制定商品创意方案。产品：无线蓝牙耳机，目标：美国Amazon市场",
        "output_content": "创意方案：1) 主图创意：运动场景+城市通勤双场景拼图，突出ANC降噪曲线；2) A+页面布局：技术解构图→使用场景→竞品对比参数表；3) 五点描述框架：ANC降噪深度、续航对比、防水等级、舒适佩戴、App智能控制。",
        "input_tokens": 420, "output_tokens": 380, "total_tokens": 800,
        "cost_cny": 0.008, "latency_ms": 2350, "status": "success",
    },
    {
        "agent_name": "VisualDesigner",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "为蓝牙耳机生成视觉设计方案，参考品牌调性：科技、运动、年轻化",
        "output_content": "视觉设计方案：1) 配色：#1a1a2e（深空蓝黑）+ #00d2ff（电光蓝）为主色调；2) 字体：Poppins Bold（标题）+ Inter Regular（正文）；3) 构图：中心对称+悬浮光效，产品位于画面中央，四周环绕声波纹效果。",
        "input_tokens": 280, "output_tokens": 350, "total_tokens": 630,
        "cost_cny": 0.005, "latency_ms": 1890, "status": "success",
    },
    {
        "agent_name": "ImageGenerator",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "Generate product image: wireless earbuds, dark background with blue neon light effects, premium quality, Amazon listing main image style, 1000x1000px",
        "output_content": "图片生成完成。生成4张变体：1) 主图-纯黑背景+产品+蓝色光晕；2) 场景图-健身房环境佩戴展示；3) 功能图-ANC降噪对比示意；4) 配件图-充电仓+替换耳塞。image_ids: img_a1b2, img_c3d4, img_e5f6, img_g7h8",
        "input_tokens": 95, "output_tokens": 180, "total_tokens": 275,
        "cost_cny": 0.012, "latency_ms": 4520, "status": "success",
    },
    {
        "agent_name": "QualityReviewer",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "审核Amazon Listing文案合规性，检查是否包含违禁词、夸大宣传",
        "output_content": "审核完成，评分：92/100。1) 无FDA药品宣称，✅；2) 未使用'Best''#1'等绝对化词汇，✅；3) 防水等级标注准确（IPX5），✅；4) 建议：续航描述'世界最长'改为'同价位最长'，⚠️。",
        "input_tokens": 340, "output_tokens": 250, "total_tokens": 590,
        "cost_cny": 0.004, "latency_ms": 1560, "status": "success",
    },
    {
        "agent_name": "ImageGenerator",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "Generate lifestyle image for wireless earbuds: person jogging in park wearing earbuds, morning light, authentic style",
        "output_content": "图片生成超时：请求在30秒内未完成。可能原因：服务器负载过高。",
        "input_tokens": 60, "output_tokens": 30, "total_tokens": 90,
        "cost_cny": 0.0, "latency_ms": 30000, "status": "timeout",
    },
    {
        "agent_name": "RequirementAnalyzer",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "分析商品：瑜伽服套装，材质：锦纶+氨纶，目标市场：欧洲（德国为主），价格€34.99",
        "output_content": "需求分析完成。欧洲瑜伽服市场分析：1) 环保材质是核心卖点（欧洲消费者对可持续面料敏感度高）；2) OEKO-TEX认证是准入门槛；3) 尺码需提供EU标准（34-46）；4) 德国市场偏好简约设计，避免过度装饰。",
        "input_tokens": 180, "output_tokens": 260, "total_tokens": 440,
        "cost_cny": 0.003, "latency_ms": 1320, "status": "success",
    },
    {
        "agent_name": "Orchestrator",
        "model_name": "qwen-plus",
        "provider": "qwen",
        "input_content": "启动商品视觉生成工作流：task_id=TASK-7108BBA8187B，商品：无线蓝牙耳机 Pro Max",
        "output_content": "工作流编排完成。任务链：RequirementAnalyzer → CreativePlanner → VisualDesigner → ImageGenerator → QualityReviewer。预计耗时：60-90秒。WebSocket通知已就绪。",
        "input_tokens": 100, "output_tokens": 120, "total_tokens": 220,
        "cost_cny": 0.001, "latency_ms": 450, "status": "success",
    },
]

SESSION_ID = f"demo-session-{uuid.uuid4().hex[:8]}"


async def main() -> None:
    conn = await asyncpg.connect(
        host="127.0.0.1", port=5432, user="postgres", password="postgres", database="cbcf"
    )

    # Ensure table exists
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_conversation_logs (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(100) NOT NULL,
            task_id VARCHAR(100),
            session_id VARCHAR(100),
            agent_name VARCHAR(50),
            model_name VARCHAR(100) NOT NULL,
            provider VARCHAR(50) NOT NULL DEFAULT 'qwen',
            input_content TEXT,
            output_content TEXT,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd DOUBLE PRECISION DEFAULT 0,
            cost_cny DOUBLE PRECISION DEFAULT 0,
            latency_ms DOUBLE PRECISION,
            status VARCHAR(20) NOT NULL DEFAULT 'success',
            error_message TEXT,
            extra_data JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    print("[OK] ai_conversation_logs table ready")

    # Check existing
    existing = await conn.fetchval("SELECT count(*) FROM ai_conversation_logs WHERE tenant_id = 'dev'")
    if existing > 0:
        print(f"[SKIP] {existing} conversations already exist for dev tenant")
        await conn.close()
        return

    now = datetime.utcnow()
    # Insert demo conversations spaced ~2 minutes apart
    for i, conv in enumerate(DEMO_CONVERSATIONS):
        offset = (len(DEMO_CONVERSATIONS) - i) * 2  # minutes ago
        ts = now - timedelta(minutes=offset)
        await conn.execute(
            """INSERT INTO ai_conversation_logs
               (tenant_id, task_id, session_id, agent_name, model_name, provider,
                input_content, output_content, input_tokens, output_tokens, total_tokens,
                cost_usd, cost_cny, latency_ms, status, metadata, created_at)
               VALUES ('dev', $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)""",
            "TASK-7108BBA8187B",
            SESSION_ID,
            conv["agent_name"],
            conv["model_name"],
            conv["provider"],
            conv["input_content"],
            conv["output_content"],
            conv["input_tokens"],
            conv["output_tokens"],
            conv["total_tokens"],
            round(conv["cost_cny"] / 7.2, 6),  # cost_usd
            conv["cost_cny"],
            int(conv["latency_ms"]),
            conv["status"],
            '{}',  # metadata JSONB
            ts,
        )

    count = await conn.fetchval("SELECT count(*) FROM ai_conversation_logs")
    print(f"[OK] Seeded {len(DEMO_CONVERSATIONS)} demo conversations ({count} total in DB)")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
