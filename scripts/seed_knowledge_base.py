"""Seed knowledge base with 30+ e-commerce documents for RAG demo.

Creates various document types: brand_guide, category_knowledge, case_study, compliance_rule.
Uses the application's DocumentProcessor + EmbeddingService pipeline.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "cbcf")

# ===== Document Content Library (30+ docs) =====

DOCUMENTS = {
    # ===== Brand Guides (10) =====
    "brand_guide_anker": {
        "title": "Anker品牌视觉规范指南",
        "doc_type": "brand_guide",
        "category": "digital",
        "metadata": {
            "keywords": ["Anker", "充电", "品牌视觉", "产品摄影", "文案规范", "logo", "色彩", "字体"],
            "language": "zh",
            "platforms": ["amazon", "ebay", "shopify"],
            "target_market": ["北美", "欧洲", "日本"],
        },
        "content": """
# Anker 品牌视觉规范指南

## 品牌概述
Anker 是全球领先的移动充电和消费电子品牌，成立于2011年。品牌以"让生活充满电能"为使命，专注于高品质充电设备、音频产品和智能家居配件。

## 品牌调性
- **核心价值**: 可靠、创新、简约
- **品牌人格**: 技术专家、值得信赖的伙伴
- **目标受众**: 25-45岁注重品质的科技产品用户

## 视觉标识规范

### Logo 使用
- 主 Logo: 蓝色文字标识 "ANKER"，字体为定制无衬线体
- Logo 最小尺寸: 印刷品 20mm，数字屏幕 60px
- 安全空间: Logo 周围至少保留 Logo 高度的 50% 空白
- 禁止拉伸、旋转、添加阴影或更改 Logo 颜色

### 品牌色彩
- 主色: Anker 蓝 (#0077C8)
- 辅色: 深灰 (#333333)、白色 (#FFFFFF)
- 强调色: 活力橙 (#FF6B35) — 仅用于促销和 CTA 按钮
- 背景色: 浅灰 (#F5F7FA)、纯白 (#FFFFFF)

### 字体规范
- 标题: Montserrat Bold / 思源黑体 Bold
- 正文: Open Sans Regular / 思源黑体 Regular
- 字号层级: H1 32px, H2 24px, H3 18px, Body 14px, Caption 12px

## 产品图片规范

### 主图要求
- 纯白背景 (RGB 255,255,255)
- 产品占据画面 85% 以上
- 分辨率不低于 2000x2000px
- 文件格式: JPEG (质量 95+) 或 PNG
- 禁止使用生活场景图作为主图

### 场景图要求
- 自然光线，真实使用场景
- 构图遵循三分法
- 画面清晰，产品突出
- 分辨率不低于 1500x1500px

### 图片风格
- 简洁干净的北欧风格
- 避免过度装饰和繁杂背景
- 色调统一，冷暖协调
- 强调产品细节和材质质感

## 文案风格

### 标题规范
- 产品名 + 核心卖点，控制在 200 字符以内
- 使用数据支撑卖点（如"26800mAh"而非"大容量"）
- 避免夸张用语（如"最好的"、"无与伦比"）

### 五点描述 (Bullet Points)
- 每条不超过 200 字符
- 前 3 点突出核心功能，后 2 点突出附加价值
- 每条以功能关键词开头，冒号分隔

### 商品描述
- 2000 字符以内
- 开头 150 字符为精简版卖点总结（移动端显示）
- 使用 HTML 段落标签，不使用内联样式

## 禁止事项
- 不得使用竞品对比图
- 不得使用未授权的模特肖像
- 不得在图片中添加促销文字和价格标签
- 不得使用低分辨率或模糊图片
- 视频不得包含未授权音乐
""",
    },
    "brand_guide_samsung": {
        "title": "Samsung品牌形象指南",
        "doc_type": "brand_guide",
        "category": "digital",
        "content": """
# Samsung 品牌形象指南

## 品牌概述
Samsung Electronics 是全球最大的消费电子制造商之一，总部位于韩国水原。品牌以"激发世界，创造未来"为愿景，业务涵盖移动设备、电视、家电和半导体。

## 品牌调性
- **核心价值**: 创新、品质、设计
- **品牌人格**: 引领潮流的技术先锋
- **目标受众**: 全年龄段科技爱好者

## 视觉标识

### 品牌色彩体系
- 主色: Samsung Blue (#1428A0)
- 辅色: 科技银 (#C0C0C0)、极夜黑 (#000000)
- 产品拍摄背景: 渐变灰（从中心向外辐射）

### 产品展示规范
- 屏幕产品需展示界面内容，禁止使用空白屏幕
- 多角度展示：正面、45度角、侧面、背面
- 配件需与主产品一起展示
- 产品图需经过色彩校准

## 内容策略
- 强调技术参数的视觉化呈现
- 使用对比图表说明产品优势
- 生活方式场景突出产品的高端定位
""",
    },
    "brand_guide_sony": {
        "title": "Sony品牌与产品展示规范",
        "doc_type": "brand_guide",
        "category": "digital",
        "content": """
# Sony 品牌与产品展示规范

## 品牌概述
Sony Corporation 是日本跨国企业集团，业务涵盖游戏、音乐、影视、电子产品和金融服务。品牌理念是"用创意和科技的力量感动世界"。

## 品牌调性
- **核心价值**: 创意、品质、激情
- **品牌人格**: 艺术家与工程师的结合体
- **目标受众**: 追求极致体验的品质用户

## 视觉标准

### 品牌色系
- 主色: Sony Black (#000000)
- 辅色: 银白 (#E8E8E8)
- 强调色: Sony 橙 (#F5A623) — 仅限包装

### 产品摄影
- 采用戏剧化布光，突出产品轮廓
- 黑色产品必须展示材质纹理差异
- 耳机类产品需展示佩戴效果
- 相机类产品需搭配镜头展示

## 文案规范
- 使用精确的技术术语
- 音频产品强调 Hi-Res Audio 认证标识
- 描述中融入"体验"、"感受"等感官词汇
- 避免与其他品牌直接对比
""",
    },
    "brand_guide_nike": {
        "title": "Nike品牌视觉营销规范",
        "doc_type": "brand_guide",
        "category": "sports",
        "content": """
# Nike 品牌视觉营销规范

## 品牌概述
Nike 是全球领先的运动鞋服品牌，总部位于美国俄勒冈州。品牌使命是"为世界上每一位运动员带来灵感和创新"。

## 品牌调性
- **核心价值**: 真实、表现、创新
- **品牌人格**: 激励人心的教练
- **目标受众**: 运动爱好者和追求运动生活方式的消费者

## 视觉标识

### Swoosh 标志使用
- 主标志: Nike Swoosh，可单独使用
- 黑色或白色 Swoosh 为主要版本
- 最小尺寸: 印刷品 10mm，数字 40px
- Swoosh 周围保持至少 Swoosh 高度的空间

### 品牌色彩
- 核心: 黑色 (#000000)、白色 (#FFFFFF)
- 运动系列强调色: 大学红、游戏蓝、金属银
- 不同运动线可使用专属配色方案

### 产品图片规范
- 运动场景拍摄强调动态感和力量感
- 球鞋拍摄需展示多角度：外侧、内侧、底部、后跟
- 服装展示需包含模特穿着效果和平铺图
- 使用专业运动员需获得授权

## 文案风格
- 简短有力的行动号召（Just Do It 风格）
- 突出技术创新（Flyknit、Air Max、React 等专有名词）
- 使用激励性语言
- 每条产品描述不超过 150 单词
""",
    },
    "brand_guide_apple": {
        "title": "Apple产品视觉与文案标准",
        "doc_type": "brand_guide",
        "category": "digital",
        "content": """
# Apple 产品视觉与文案标准

## 品牌概述
Apple Inc. 是全球最具价值的科技公司，以创新的硬件、软件和服务闻名。品牌理念强调简约设计和卓越用户体验。

## 品牌调性
- **核心价值**: 简约、创新、人性化
- **品牌人格**: 优雅的革新者
- **目标受众**: 追求品质生活和创意表达的用户

## 视觉规范

### 产品摄影
- 纯白或纯黑背景
- 极简风格，无多余元素
- 产品居中，对称构图
- 光源柔和均匀，避免硬阴影
- 分辨率至少 3000x3000px

### 屏幕内容展示
- 必须使用 Apple 官方提供的屏幕截图
- 禁止显示第三方应用界面（除非已授权）
- 设备角度需精确控制

## 文案指南
- 简洁、清晰、富有韵律感
- 大量使用短句和断句
- 标题通常不超过 8 个词
- 强调"体验"而非"规格"
""",
    },
    "brand_guide_dyson": {
        "title": "Dyson品牌工程美学规范",
        "doc_type": "brand_guide",
        "category": "home",
        "content": """
# Dyson 品牌工程美学规范

## 品牌概述
Dyson 是英国科技公司，以创新家电产品闻名，包括无绳吸尘器、空气净化器、吹风机等。

## 品牌调性
- **核心价值**: 工程创新、设计美学、解决问题
- **品牌人格**: 精益求精的发明家
- **目标受众**: 中高收入家庭，注重生活品质

## 视觉规范
- 产品拍摄强调科技感和工程结构
- 常使用剖面图展示内部技术
- 色彩以铁灰、镍色、紫色为主
- 禁止过度美化，需真实展示产品材质

## 文案要点
- 强调专利技术和工程突破
- 使用数据和测试结果支撑
- 避免夸张营销用语
""",
    },
    "brand_guide_loreal": {
        "title": "L'Oreal美妆品牌视觉规范",
        "doc_type": "brand_guide",
        "category": "beauty",
        "content": """
# L'Oreal 美妆品牌视觉规范

## 品牌概述
L'Oreal 是全球最大的化妆品集团，总部位于法国。品牌口号"因为你值得拥有"深入人心。

## 品牌调性
- **核心价值**: 美丽、科学、包容
- **品牌人格**: 优雅自信的美丽顾问
- **目标受众**: 18-55岁追求美丽的女性

## 视觉规范
- 产品主图需使用柔光箱拍摄
- 色彩还原必须准确（使用色卡校准）
- 模特妆容需自然精致
- 包装特写需清晰展示成分标签

## 文案规范
- 使用科学术语描述护肤功效
- 避免过度承诺（不使用"瞬间"、"立即"等词）
- 包含成分说明和使用方法
""",
    },
    "brand_guide_petco": {
        "title": "PetSafe宠物用品品牌指南",
        "doc_type": "brand_guide",
        "category": "pet",
        "content": """
# PetSafe 宠物用品品牌指南

## 品牌概述
PetSafe 是领先的宠物用品品牌，提供从训练项圈到智能喂食器的全系列产品。

## 品牌调性
- **核心价值**: 关爱、安全、创新
- **品牌人格**: 值得信赖的宠物专家
- **目标受众**: 宠物主人，特别是首次养宠用户

## 视觉规范
- 图片中必须展示真实宠物与产品的互动
- 宠物必须处于自然、舒适的状态
- 不展示任何可能引起不适的场景
- 色彩温暖，避免冷色调

## 文案规范
- 语言友好亲切，用"毛孩子"等温馨词汇
- 强调安全认证和 veterinarians 推荐
- 必须包含适用宠物品种和体重范围
""",
    },
    "brand_guide_owala": {
        "title": "Owala运动水具品牌视觉手册",
        "doc_type": "brand_guide",
        "category": "sports",
        "content": """
# Owala 运动水具品牌视觉手册

## 品牌概述
Owala 是北美领先的运动水具品牌，以创新的 FreeSip 吸管设计和多彩配色闻名。

## 品牌调性
- **核心价值**: 乐趣、功能、个性
- **品牌人格**: 充满活力的生活伙伴
- **目标受众**: 18-35岁活跃生活方式的年轻消费者

## 视觉标识
- 品牌色系: 明亮清新，以蒂芙尼蓝、珊瑚粉、柠檬黄为主
- 产品摄影: 强调色彩搭配和材质对比
- 场景图: 健身房、户外徒步、办公桌等多元场景
- 社交风格: 适合 Instagram/TikTok 的鲜艳视觉效果

## 文案风格
- 轻松活泼，使用感叹号和表情符号
- 强调个性化色彩选择
- 突出 FreeSip 专利设计
""",
    },
    "brand_guide_dewalt": {
        "title": "DeWalt专业工具品牌规范",
        "doc_type": "brand_guide",
        "category": "other",
        "content": """
# DeWalt 专业工具品牌规范

## 品牌概述
DeWalt 是 Stanley Black & Decker 旗下的专业电动工具品牌，以黄黑色品牌配色闻名。

## 品牌调性
- **核心价值**: 坚固、专业、可靠
- **品牌人格**: 经验丰富的工地老手
- **目标受众**: 建筑承包商、木工、DIY 高阶爱好者

## 视觉规范
- 黄黑配色必须严格遵守色号标准（黄色 PMS 1235C）
- 产品图需展示作业场景（工地、车间）
- 强调工具的使用状态而非静态摆放
- 模特需穿着专业防护装备

## 文案规范
- 使用行业术语和规格参数
- 强调耐用性测试数据
- 对比无刷电机与有刷电机的优势
""",
    },

    # ===== Category Knowledge (10) =====
    "category_mobile_power": {
        "title": "移动电源品类知识库",
        "doc_type": "category_knowledge",
        "category": "digital",
        "content": """
# 移动电源品类知识库

## 品类概述
移动电源（Power Bank）是随身携带的充电设备，为手机、平板等设备提供应急电力。全球市场规模预计 2027 年达到 270 亿美元。

## 核心参数解读

### 容量 (mAh)
- 5000mAh: 适合应急充电，约可为手机充电 1 次
- 10000mAh: 日常使用主流容量，约可充电 2 次
- 20000mAh: 适合重度用户和多设备用户
- 26800mAh+: 专业级容量，需注意航空携带限制（限额 100Wh≈27000mAh）

### 输出功率
- 5V/2A (10W): 基础充电
- PD 18W: 支持 iPhone 快充
- PD 30W: 支持 iPad 和轻薄本
- PD 65W+: 支持笔记本电脑充电

### 接口类型
- USB-A: 传统输出口
- USB-C: 双向充放电，PD 协议
- Micro-USB: 老旧充电口（逐渐淘汰）
- Lightning: Apple 设备专用

## 目标市场
- 北美: 高容量偏好，注重品牌和认证
- 欧洲: 注重环保和能效标识
- 日本: 偏好轻薄小巧设计
- 东南亚: 性价比敏感

## 竞争格局
- 高端: Anker, Mophie, Belkin
- 中端: Aukey, RAVPower, Xiaomi
- 入门: Romoss, Baseus, 各类白牌

## Listing 要点
- 必须标注民航携带限制说明（100Wh/27000mAh 以上需申报）
- 突出快充协议兼容性（PD/QC/PPS）
- 展示多口同时充电能力
""",
    },
    "category_headphones": {
        "title": "耳机品类知识与卖点提炼",
        "doc_type": "category_knowledge",
        "category": "digital",
        "content": """
# 耳机品类知识与卖点提炼

## 品类细分
- **头戴式 (Over-Ear)**: 音质最佳，适合家庭和办公室使用
- **入耳式 (In-Ear)**: 便携性好，适合运动和通勤
- **真无线 (TWS)**: 增长最快的细分市场
- **骨传导**: 适合运动场景，保持环境感知

## 核心技术参数

### 降噪技术
- ANC (主动降噪): 通过反向声波消除环境噪音
- ENC (环境降噪): 通话时过滤背景噪音
- 被动降噪: 物理隔音，依赖耳罩材质和结构

### 音频编码
- SBC: 基础蓝牙编码
- AAC: Apple 设备优化
- aptX/aptX HD: 高通高品质编码
- LDAC: Sony 高解析度编码 (最高 990kbps)

### 续航与充电
- TWS 单次续航: 4-8 小时（主流水平）
- 充电盒补充: 通常 3-5 次完整充电
- 快充: 10 分钟充电可用 1-2 小时

## Listing 亮点策略
- 降噪耳机: 展示降噪前后对比
- 运动耳机: 强调 IPX 防水等级
- 游戏耳机: 突出低延迟模式
- 商务耳机: 强调通话质量和多设备连接

## 合规注意事项
- 蓝牙认证标识
- 电池安全认证 (CE, FCC, UL)
- 射频发射功率限制（各国不同）
""",
    },
    "category_speakers": {
        "title": "蓝牙音箱市场分析与卖点策略",
        "doc_type": "category_knowledge",
        "category": "digital",
        "content": """
# 蓝牙音箱市场分析与卖点策略

## 市场概况
全球便携式蓝牙音箱市场 2024 年约 80 亿美元，预计以 CAGR 12% 增长至 2030 年。主要驱动因素包括户外活动增加、智能家居普及和音频技术进步。

## 产品分类
- **便携式**: 手掌大小，重量 <500g，适合户外
- **家用式**: 体积较大，注重音质和智能功能
- **派对音箱**: 大功率输出，带灯光效果
- **户外三防**: IP67 防水防尘防摔，适合极端环境

## 关键技术指标
- 驱动单元尺寸: 40mm (便携), 50-60mm (家用)
- 输出功率: 5W-30W (便携), 50W+ (家用/派对)
- 蓝牙版本: 5.3 为目前主流，5.4 已推出
- 防水等级: IPX4 (防溅), IPX7 (浸水 1m/30min), IP67 (防尘防水)
- 续航: 8-24 小时（便携），有线供电（家用）

## Listing 卖点策略
- 户外场景: 突出防水、防摔、长续航
- 家居场景: 突出音质、语音助手、多房间同步
- 派对场景: 突出灯光秀、重低音、串联功能

## 竞争品牌
- JBL: 市场领导者，Flip/Charge/Go 系列
- Bose: 高端市场，SoundLink 系列
- Ultimate Ears: 年轻市场，BOOM/MEGABOOM 系列
- Marshall: 复古设计，摇滚风格
- Sony: 技术流，Extra Bass 系列
""",
    },
    "category_smart_home": {
        "title": "智能家居品类分析",
        "doc_type": "category_knowledge",
        "category": "home",
        "content": """
# 智能家居品类分析

## 市场概述
全球智能家居市场 2024 年规模约 1200 亿美元，涵盖智能音箱、安防、照明、温控、家电等子品类。

## 主要子品类

### 智能音箱
- 作为智能家居入口设备
- 主流: Amazon Echo, Google Nest, Apple HomePod
- 关键功能: 语音控制、音乐播放、设备联动

### 智能安防
- 智能门锁、摄像头、门铃、传感器
- 隐私安全是用户首要关注点
- Ring (Amazon), Arlo, Eufy 为主要品牌

### 智能照明
- Philips Hue 为市场领导者
- 支持场景模式、定时、语音控制
- RGB 氛围灯增长迅速

### 智能家电
- 扫地机器人: Roomba, Roborock
- 智能空调: 温度自调节，远程控制
- 智能厨房: 精确温控、菜谱联动

## Listing 要点
- 必须明确标注支持的生态系统（Alexa/Google/Apple）
- 注明是否需要 HUB/网关
- 安装复杂度说明
""",
    },
    "category_sportswear": {
        "title": "运动服装品类电商运营指南",
        "doc_type": "category_knowledge",
        "category": "sports",
        "content": """
# 运动服装品类电商运营指南

## 市场细分
- **专业运动**: 跑步、瑜伽、篮球等专项装备
- **运动休闲 (Athleisure)**: 运动与日常穿搭的融合
- **户外运动**: 登山、滑雪、露营等
- **运动内衣**: 运动 Bra、压缩衣等

## 面料技术关键词
- Dri-FIT (Nike): 吸湿排汗
- Climalite (Adidas): 透气速干
- HeatGear (Under Armour): 热天降温
- ColdGear (Under Armour): 冷天保温
- GORE-TEX: 防水透气膜

## 尺码与合身度
- 使用标准尺码表，包含各部位测量说明
- 提供合身度说明: Slim Fit / Regular Fit / Loose Fit
- 模特身高体重信息帮助消费者判断
- 建议同时提供英寸和厘米单位

## Listing 图片要求
- 至少包含: 正面、背面、侧面、细节
- 建议包含: 模特穿着效果、面料特写、尺码对比
- 使用视频展示运动中的服装效果（尤为关键）
- 色彩需在白光下拍摄确保准确
""",
    },
    "category_skincare": {
        "title": "护肤品跨境电商知识库",
        "doc_type": "category_knowledge",
        "category": "beauty",
        "content": """
# 护肤品跨境电商知识库

## 产品分类
- **清洁类**: 洁面乳、卸妆油、去角质
- **保湿类**: 面霜、精华、面膜
- **防晒类**: 物理防晒、化学防晒、混合防晒
- **功效类**: 抗衰老、美白、祛痘

## 核心成分知识
- 透明质酸 (Hyaluronic Acid): 保湿锁水
- 维生素 C (Vitamin C): 美白抗氧化
- 视黄醇 (Retinol): 抗衰老，促进胶原蛋白
- 烟酰胺 (Niacinamide): 控油修复
- 水杨酸 (Salicylic Acid): 祛痘去角质
- 神经酰胺 (Ceramides): 修复皮肤屏障

## 跨境合规要点
- 欧盟: CPNP 备案，禁用 1300+ 成分
- 美国: FDA 自愿注册，成分标签规范
- 中国: NMPA 备案，动物实验要求（部分品类）
- 日本: 医药部外品审批
- 韩国: KFDA 认证，功能性化妆品申报

## Listing 策略
- 突出核心成分和浓度
- 展示质地（清爽/滋润/厚重）
- 注明适合肤质（油性/干性/混合/敏感）
- 使用前后对比（注意合规）
""",
    },
    "category_pet_supplies": {
        "title": "宠物用品跨境电商指南",
        "doc_type": "category_knowledge",
        "category": "pet",
        "content": """
# 宠物用品跨境电商指南

## 市场趋势
全球宠物用品市场 2024 年约 3200 亿美元，北美占比 40%。跨境电商增长最快的子品类为智能宠物用品和天然宠物食品。

## 子品类分析

### 宠物食品
- 干粮、湿粮、冻干、生食
- 天然/有机趋势强劲
- 功能性食品（关节保护、毛发护理）

### 宠物智能用品
- 自动喂食器: WiFi 控制、定时定量、摄像头
- 智能饮水机: 循环过滤、UV 杀菌
- GPS 追踪器: 实时定位、电子围栏
- 智能猫砂盆: 自动清理、健康监测

### 宠物出行
- 航空箱: IATA 认证要求
- 车载座椅: 安全固定、防水材质
- 背包: 通风设计、人体工学

## Listing 规范
- 必须标注适用宠物品种、体型/体重范围
- 食品类需提供完整成分表和营养分析
- 电子类需提供电池类型和续航信息
- 所有产品需标注安全警告
""",
    },
    "category_baby": {
        "title": "母婴用品品类操作手册",
        "doc_type": "category_knowledge",
        "category": "baby",
        "content": """
# 母婴用品品类操作手册

## 品类特点
母婴用品对安全性要求极高，消费者决策时品牌信任度影响最大。跨境销售需特别注意各国安全标准差异。

## 安全合规
- 美国: CPSC 认证，ASTM F963 玩具安全标准
- 欧盟: CE 标记，EN 71 玩具安全标准
- 日本: ST 标准，食品卫生法
- 中国: GB 强制性标准，3C 认证

## 材质要求
- BPA-Free: 奶瓶和餐具的标配
- 食品级硅胶: 牙胶、奶嘴材质
- 有机棉: 婴儿服装和寝具
- 无毒水性漆: 木质玩具

## Listing 特殊要求
- 必须标注适用月龄/年龄
- 提供材质安全认证标识
- 洗涤/消毒说明必须完整
- 警告标签必须醒目
- 婴儿床等大件需注明组装要求
""",
    },
    "category_power_tools": {
        "title": "电动工具国际市场分析",
        "doc_type": "category_knowledge",
        "category": "other",
        "content": """
# 电动工具国际市场分析

## 市场格局
全球电动工具市场 2024 年约 450 亿美元，以无刷电机和锂电技术为创新驱动。

## 主要品牌
- 专业级: DeWalt, Milwaukee, Makita, Bosch Professional
- 消费级: Black+Decker, Ryobi, Craftsman
- 高性价比: 中国品牌 (WORX, EGO)

## 技术趋势
- 无刷电机: 效率提升 30%，寿命延长 50%
- 锂电池平台: 同品牌多工具共享电池
- 智能工具: App 连接，扭矩控制，使用记录

## 电压平台
- 12V: 轻量级，适合精密作业
- 18V/20V MAX: 主力电压平台
- 40V+: 高功率，适用于户外设备

## 跨境注意事项
- 电压/插头适配（充电器）
- 运输限制（锂电池 UN38.3 认证）
""",
    },
    "category_cookware": {
        "title": "厨具品类国际市场洞察",
        "doc_type": "category_knowledge",
        "category": "home",
        "content": """
# 厨具品类国际市场洞察

## 市场概况
全球厨具市场持续增长，消费者对健康烹饪和设计美学的需求推动了高端化趋势。

## 材质趋势
- 不锈钢: 经典耐用，18/10 食品级为标杆
- 铸铁: 复古风潮，Lodge/Staub/Le Creuset
- 不粘涂层: 陶瓷涂层替代 PTFE 趋势
- 碳钢: 专业厨师首选，需养护

## 热源兼容性
- 燃气灶: 所有材质通用
- 电磁炉: 需磁性底部（铸铁、不锈钢需磁性复底）
- 电陶炉: 需平底设计
- 烤箱: 需注明最高耐温温度

## Listing 策略
- 展示使用场景和成品菜品
- 提供保养说明（是否可进洗碗机）
- 重量信息（国际运费敏感）
""",
    },

    # ===== Case Studies (5) =====
    "case_study_anker_amazon": {
        "title": "Anker亚马逊成功案例：从0到品类第一",
        "doc_type": "case_study",
        "category": "digital",
        "content": """
# Anker 亚马逊成功案例：从0到品类第一

## 背景
Anker 于 2011 年成立于深圳，最初在亚马逊美国站销售笔记本电脑电池。凭借优质产品和精准营销，5 年内成为亚马逊充电品类第一名。

## 关键策略

### 产品策略
- 选择蓝海品类（2011 年移动电源竞争度低）
- 品质优先于成本（使用 LG/Panasonic 电芯）
- 快速迭代（每年推出 20+ 新品）

### Listing 优化
- 使用高清产品主图（2000x2000px 白底图）
- 场景图+功能标注（信息图模式）
- 五点描述数据化（"26800mAh"而非"超大容量"）
- A+ 内容运用对比图和场景图

### 评论管理
- 主动跟进客户邮件（售后关怀）
- 使用 Vine 计划获取早期评价
- 负面评价 24 小时内响应

## 成果
- 移动电源品类 Best Seller 标签
- 月销 10 万+ 台
- 评分 4.5 星以上
- 复购率 18%

## 可复制经验
1. 品类选择需具备上升趋势
2. 产品品质是 Listing 优化的前提
3. 数据化卖点比形容词更有说服力
4. 售后服务是评论管理的根本
""",
    },
    "case_study_soundcore": {
        "title": "Soundcore耳机品牌出海案例",
        "doc_type": "case_study",
        "category": "digital",
        "content": """
# Soundcore 耳机品牌出海案例

## 项目背景
Soundcore 是 Anker Innovations 旗下音频品牌，2018 年独立运营。目标是在音频市场复制 Anker 的成功模式。

## 市场进入策略
- 首发市场: 美国 Amazon
- 价格带: $30-$80（避开 Bose/Sony $200+ 主战场）
- 核心受众: 18-35岁科技爱好者

## 产品创新
- Liberty Air 系列: 对标 AirPods，半价策略
- Life Q 系列: ANC 功能下放至百元价位
- Space 系列: 首创可伸缩头梁设计

## Listing 优化要点
- 突出 ANC 降噪深度（dB 数值）
- 续航对比图表（vs AirPods/Sony/Bose）
- 真人佩戴图展示不同耳型适配
- 视频展示通透模式和降噪模式切换
- A+ 模块讲解 LDAC 高解析度音频

## 营销推广
- 与科技 YouTuber 合作测评
- Reddit 社区运营（r/headphones）
- Vine 计划 + 早期评论人计划打开评价

## 成果
- Liberty 4 NC 进入亚马逊 TWS Top 20
- 品牌搜索量年增长 300%
""",
    },
    "case_study_roborock": {
        "title": "石头科技扫地机器人出海之路",
        "doc_type": "case_study",
        "category": "home",
        "content": """
# 石头科技扫地机器人出海之路

## 公司背景
Roborock（石头科技）成立于 2014 年，是小米生态链企业。2017 年推出自有品牌，主攻海外高端扫地机器人市场。

## 出海战略

### 第一步：产品差异化
- LDS 激光导航 vs 竞品视觉导航
- 拖地功能集成（扫拖一体）
- 自动集尘基站（减少人工介入）

### 第二步：技术品牌化
- 将 LDS 导航包装为"Precision LiDAR Navigation"
- 强调 APP 功能（分区清扫、虚拟墙、定时）
- 展示智能避障（识别宠物粪便、线缆）

### 第三步：电商精细化
- Listing 标题格式: "Roborock [型号] Robot Vacuum and Mop Combo, with LiDAR Navigation, 3000Pa Suction, 180mins Runtime"
- 视频展示: 自动集尘、爬坡越障、APP 操作
- 对比图: 清扫路径 vs 随机碰撞式机器人

## 关键成功因素
1. 产品力是根本（导航技术领先竞品一代）
2. 技术参数可视化（吸力 Pa 值、续航分钟数）
3. A+ 内容系统讲解技术原理
4. 用户生成内容利用（宠物友好视频天然传播）

## 数据成果
- 2023 年海外营收超 40 亿元人民币
- Amazon 北美扫地机器人品类 Top 5
- 复购率 12%（配件/耗材）
""",
    },
    "case_study_halara": {
        "title": "Halara运动休闲品牌TikTok营销案例",
        "doc_type": "case_study",
        "category": "clothing",
        "content": """
# Halara 运动休闲品牌 TikTok 营销案例

## 品牌背景
Halara 是 2020 年成立的 DTC 运动休闲品牌，定位"将运动科技融入日常穿搭"。凭借 TikTok 病毒式营销快速崛起。

## 营销策略

### TikTok 优先战略
- 与 1000+ 微网红合作（而非少数大 V）
- 发布真实穿搭视频（非精修广告）
- #HalaraHaul 话题累计 10 亿+ 播放
- 利用用户生成内容(UGC)作为广告素材

### Listing 优化特点
- 真实身材模特（XS-4XL 全尺码展示）
- 运动视频展示面料弹性（深蹲、跳跃测试）
- 色彩多样（每款 15+ 颜色选项）
- 强调不透明和抗起球特性

### 独立站 + Amazon 双渠道
- 独立站: 品牌体验 + 会员体系
- Amazon: 流量获取 + 快速配送
- 两渠道价格统一，促销差异化

## 可复制经验
1. 短视频内容需真实自然，拒绝过度制作
2. 微网红性价比远高于头部 KOL
3. 产品品质是口碑传播的基础
4. 数据驱动的广告投放优化
""",
    },
    "case_study_ecoflow": {
        "title": "EcoFlow便携储能电源品牌案例",
        "doc_type": "case_study",
        "category": "digital",
        "content": """
# EcoFlow 便携储能电源品牌案例

## 公司背景
EcoFlow 成立于 2017 年，专注于便携式储能电源和可再生能源解决方案。C 轮融资过亿美元，全球用户超 300 万。

## 产品特色
- X-Boost 技术: 可驱动额定功率 2 倍的设备
- X-Stream 快充: 1 小时充至 80%
- 磷酸铁锂电池: 3000+ 次循环寿命
- APP 智能控制: 远程管理、能耗监控

## 出海策略

### 独立站 + 众筹启动
- Kickstarter 首发，获得种子用户和资金
- 独立站建立品牌形象和用户社区
- 然后扩展至 Amazon、Home Depot 等渠道

### Listing 策略
- 主图突出功率和容量（"2016Wh"、"2400W"）
- 场景图: 露营、房车、家庭应急、工地
- 信息图: 充电方式图示（太阳能、车充、市电、发电机）
- 视频: 同时驱动多个设备的实测

### 内容营销
- YouTube 露营/房车频道合作
- 极端环境测试（沙漠、雪地）
- 家庭应急教育内容（停电备灾）

## 成果与启示
- 2023 年全球销售额超 10 亿美元
- Amazon 储能电源品类 Best Seller
- 核心启示: 技术创新 + 场景化内容 = 品类领导地位
""",
    },

    # ===== Compliance Rules (8) =====
    "compliance_amazon": {
        "title": "Amazon平台商品合规规则汇总",
        "doc_type": "compliance_rule",
        "category": "digital",
        "content": """
# Amazon 平台商品合规规则汇总

## 图片规范
- 主图必须为纯白背景 (RGB 255,255,255)
- 主图不得包含文字、Logo、水印（产品自带的除外）
- 图片最短边不低于 500px，建议 1000px+
- 图片不得包含促销信息、价格、运费等
- 主图产品必须占画面 85% 以上
- 服装类主图必须是平铺或模特穿着
- 禁止使用占位图（Coming Soon、No Image Available 等）

## 标题规范
- 长度不超过 200 字符
- 禁止全大写（品牌名除外）
- 禁止促销信息（Best Seller、Free Shipping 等）
- 禁止特殊字符（!、*、$ 等，品牌名中自带的除外）
- 格式: [品牌] + [型号] + [核心特征] + [尺寸/颜色] + [数量]

## 五点描述规范
- 每条不超过 500 字符（建议 200 字符以内）
- 禁止促销和定价信息
- 禁止公司信息、联系方式
- 禁止引导离开亚马逊的内容

## 禁止行为
- 评论操纵（刷单、索要好评、改差评）
- 变体滥用（不相关产品绑定）
- 关键词堆砌和品牌名滥用
- 敏感品类需提前获得销售权限
""",
    },
    "compliance_eu": {
        "title": "欧盟市场商品合规要求",
        "doc_type": "compliance_rule",
        "category": "digital",
        "content": """
# 欧盟市场商品合规要求

## CE 标志
- 大部分产品需 CE 标志才能进入欧盟市场
- CE 标志表示产品符合欧盟健康、安全和环保标准
- 需保留技术文档和符合性声明 (DoC) 至少 10 年

## RoHS 指令
- 限制电子电气设备中有害物质使用
- 限制铅、汞、镉、六价铬、PBB、PBDE 等
- 2019 年新增 4 种邻苯二甲酸酯限制

## REACH 法规
- 化学品注册、评估、授权和限制
- SVHC（高度关注物质）清单定期更新
- 含 SVHC 超 0.1% 需向消费者告知

## GDPR 数据保护
- 处理欧盟用户数据必须合规
- 隐私政策需清晰透明
- 用户享有数据访问、更正、删除权

## 包装与包装废弃物指令
- 限制包装中重金属含量
- 要求包装可回收或可重复使用
- 德国、法国等有延伸的包装法要求（EPR 注册）

## WEEE 指令
- 电子废弃物回收责任
- 需在目标国注册 WEEE
- 产品标注垃圾桶打叉标志
""",
    },
    "compliance_fda": {
        "title": "美国FDA化妆品法规合规指南",
        "doc_type": "compliance_rule",
        "category": "beauty",
        "content": """
# 美国 FDA 化妆品法规合规指南

## 法规框架
- 美国 FDA 依据《联邦食品、药品和化妆品法》(FD&C Act) 监管化妆品
- 2022 年 MoCRA 法案新增多项化妆品监管要求

## 标签要求
- 产品标识（产品名称和用途）
- 净含量（英制 + 公制双标注）
- 成分表（按含量降序排列，使用 INCI 名称）
- 制造商/经销商信息（名称和地址）
- 警告声明（如适用）

## 禁用/限制成分
- 水银化合物: 禁用（除眼部防腐剂微量使用）
- 氯仿: 禁用
- 亚甲基二醇: 禁用（甲醛释放体）
- 防晒剂: 按 OTC 药品监管，需 FDA 专论成分

## 宣称规范
- 结构/功能宣称 vs 药品宣称的界限
- "治疗"、"治愈"、"预防" 属于药品宣称
- "改善"、"增强"、"减少" 可能属于化妆品宣称
- 任何改变身体结构或功能的宣称需要药品审批

## 不良反应报告
- MoCRA 要求制造商在 15 天内报告严重不良事件
- 保留不良反应记录至少 6 年
""",
    },
    "compliance_aliexpress": {
        "title": "速卖通平台规则与Listing禁忌",
        "doc_type": "compliance_rule",
        "category": "digital",
        "content": """
# 速卖通平台规则与 Listing 禁忌

## 标题规范
- 长度限制 128 个字符
- 格式: 核心词 + 属性词 + 场景词
- 禁止全大写、重复关键词堆砌

## 图片规范
- 主图建议 800x800px 以上
- 支持白底和场景主图
- 第 6 张图建议为包装图
- 禁止图片中包含联系方式

## 禁止品类的 Listing 注意
- 仿品: 零容忍，严查
- 食品/保健品: 需提供相关资质
- 带电产品: 需标注电池类型和运输方式
- 液体/粉末: 需注明特殊包装和物流限制

## 价格策略
- 标低价吸引点击但在 SKU 中加价属于搜索作弊
- 运费模板不能虚高
- 禁止 SKU 作弊（用不卖的低价 SKU 引流）

## 店铺指标
- 及时发货率: ≥ 90%
- 货不对版纠纷率: ≤ 5%
- 好评率: 影响搜索排名
""",
    },
    "compliance_amazon_jp": {
        "title": "日本亚马逊出品ルールとコンプライアンス",
        "doc_type": "compliance_rule",
        "category": "digital",
        "content": """
# 日本亚马逊出品规则与合规要求

## 语言要求
- Listing 全部使用日语
- 标题、描述、五点必须日文
- 不能仅有英文或中文翻译

## 产品合规
- 电器产品需 PSE 标志
- 无线产品需技适 MARK (TELEC 认证)
- 食品/化妆品需厚生劳动省许可
- 儿童玩具需 ST 标准认证

## 税务
- JCT (消费税) 注册要求
- 2025 年起平台代扣代缴制度

## 日本特有的 Listing 习惯
- 标题格式: 【品牌名】商品名 型号 颜色 尺寸
- 5 点描述以 "・" 开头
- 描述中使用颜文字和装饰符（平台规则内）
- 包装和说明书必须日文

## 客户期望
- 响应速度期望高（24 小时内）
- 包装必须精美无破损
- 退换货政策需清晰
""",
    },
    "compliance_children": {
        "title": "儿童产品安全合规要求",
        "doc_type": "compliance_rule",
        "category": "baby",
        "content": """
# 儿童产品安全合规要求

## 美国 CPSIA 要求
- 所有儿童产品需经 CPSC 认可的实验室检测
- 铅含量限制: 总铅 ≤ 100ppm (基材)，≤ 90ppm (涂层)
- 邻苯二甲酸酯: 限制 8 种特定物质
- 儿童产品证书 (CPC): 制造商/进口商必须出具
- 永久性追踪标签: 标注制造商、生产日期、批次号

## 欧盟要求
- CE 标志 + EN 71 系列测试
- REACH 法规下的 SVHC 申报
- 食品接触材料需符合 EU 1935/2004

## 小零件警告
- 3 岁以下儿童产品不得含小零件
- 3-6 岁产品需标注窒息危险警告
- 尖锐边缘和尖端限制

## 易燃性
- 儿童睡衣必须符合 16 CFR 1615/1616 标准
- 纺织品阻燃处理需标注
""",
    },
    "compliance_walmart": {
        "title": "Walmart Marketplace卖家合规指南",
        "doc_type": "compliance_rule",
        "category": "digital",
        "content": """
# Walmart Marketplace 卖家合规指南

## 入驻要求
- 企业资质（美国公司或授权代理）
- 产品责任险（一般 $1,000,000 起）
- 仓库位于美国（或使用 WFS）
- 良好的电商运营历史

## Listing 规范
- 标题不超过 200 字符
- 使用标准产品标识码（UPC/GTIN/EAN）
- 图片白底为主（部分品类接受场景图）
- 属性完整率要求 80% 以上

## 价格政策
- 价格领先政策: 不得在 Walmart 价格高于其他渠道
- 比价政策: 平台会自动匹配外部低价
- MAP (最低广告价格) 需遵守

## 物流要求
- 2 天达标签（TwoDay Delivery）
- 建议使用 WFS (Walmart Fulfillment Services)
- 准时送达率 ≥ 95%

## 退货政策
- 至少 30 天退货期
- 部分品类更长（电子产品 90 天）
- 退货标签需提供
""",
    },
    "compliance_shopify": {
        "title": "Shopify独立站合规运营手册",
        "doc_type": "compliance_rule",
        "category": "digital",
        "content": """
# Shopify 独立站合规运营手册

## 法律页面
- Privacy Policy: GDPR/CCPA 要求，需独立撰写
- Terms of Service: 保护卖家权益
- Refund Policy: 退货退款规则透明
- Shipping Policy: 物流时效和费用说明
- 各页面需可访问并在 footer 中链接

## 支付合规
- PCI DSS 合规: 使用 Shopify Payments 或 PayPal 等已认证渠道
- 不得收集完整信用卡信息
- 3D Secure 认证（欧洲 Strong Customer Authentication）

## 税务
- 美国: 各州经济纽带 (Economic Nexus) 规则不同
- 欧盟: OSS (One Stop Shop) 统一申报
- 英国: VAT 注册门槛 £85,000
- 加拿大: GST/HST 注册

## Cookie 同意
- 欧盟: 需主动同意（非默示）
- CCPA: 需提供退出选项
- Cookie Banner 需列出所有 Cookie 用途

## 可访问性 (ADA)
- 图片需有 alt 标签
- 颜色对比度需达标
- 键盘可导航
""",
    },
}


def _build_metadata(doc_data: dict) -> dict:
    """Auto-build metadata from document content and metadata.

    Extracts keywords from title + headings, derives target platforms
    and markets from content analysis.

    Args:
        doc_data: Document data dict with title, content, doc_type, category.

    Returns:
        Metadata dict with keywords, language, platforms, target_market.
    """
    import re

    title = doc_data.get("title", "")
    content = doc_data.get("content", "")
    doc_type = doc_data.get("doc_type", "")
    category = doc_data.get("category", "")

    # Extract keywords from title words + markdown headings
    keywords: list[str] = []
    # From title: split by common separators
    title_words = re.split(r"[-—·、：: 　]", title)
    for w in title_words:
        w = w.strip()
        if len(w) >= 2 and w not in {"品牌", "指南", "规范", "手册", "分析", "案例", "知识", "要求", "规则", "标准", "市场"}:
            keywords.append(w)

    # From markdown headings (## and ###)
    heading_pattern = re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)
    for h in heading_pattern:
        h = h.strip()
        if len(h) <= 12 and h not in keywords:
            keywords.append(h)

    # Top 10 keywords max
    keywords = keywords[:10]

    # Derive platforms from content mentions
    platform_keywords = {
        "amazon": "Amazon|亚马逊|amazon",
        "ebay": "eBay|ebay",
        "shopify": "Shopify|shopify|独立站",
        "temu": "TEMU|temu",
        "walmart": "Walmart|walmart|沃尔玛",
        "aliexpress": "AliExpress|速卖通|aliexpress",
        "lazada": "Lazada|lazada",
        "shopee": "Shopee|shopee",
    }
    platforms: list[str] = []
    for p, pattern in platform_keywords.items():
        if re.search(pattern, content, re.IGNORECASE):
            platforms.append(p)
    if not platforms:
        platforms = ["amazon", "ebay", "shopify"]  # default

    # Derive target markets from content mentions
    market_keywords = {
        "北美": "北美|美国|加拿大|United States|America|Canada",
        "欧洲": "欧洲|欧盟|EU|德国|法国|英国|Europe|Germany|France|UK",
        "日本": "日本|Japan|日语",
        "东南亚": "东南亚|Southeast Asia|泰国|越南|印尼",
        "韩国": "韩国|Korea",
        "拉美": "拉美|Latin America|巴西|墨西哥",
    }
    target_market: list[str] = []
    for m, pattern in market_keywords.items():
        if re.search(pattern, content, re.IGNORECASE):
            target_market.append(m)
    if not target_market:
        target_market = ["北美", "欧洲"]  # default

    return {
        "keywords": keywords,
        "language": "zh",
        "platforms": platforms,
        "target_market": target_market,
        "doc_type": doc_type,
        "category": category,
    }


async def main():
    from src.rag.document_processor import DocumentProcessor
    from src.rag.embeddings import EmbeddingService
    from src.db.vector_store import VectorStore
    from src.db.postgres import get_db_session
    from src.db.models import KnowledgeDoc
    from sqlalchemy import text
    import time

    processor = DocumentProcessor()
    embedding_service = EmbeddingService()

    tenant_id = "dev"
    total_chunks = 0
    success_count = 0
    error_count = 0

    async with get_db_session() as session:
        # Clear existing knowledge data for clean seed
        await session.execute(text("DELETE FROM knowledge_chunks WHERE tenant_id = :tid"), {"tid": tenant_id})
        await session.execute(text("DELETE FROM knowledge_docs WHERE tenant_id = :tid"), {"tid": tenant_id})
        await session.commit()
        print("Cleared existing knowledge data")

        vector_store = VectorStore()

        for doc_key, doc_data in DOCUMENTS.items():
            try:
                print(f"\nProcessing: {doc_data['title']} [{doc_data['doc_type']}]...")

                # Parse content
                parsed = processor.parse_content(
                    content=doc_data["content"],
                    title=doc_data["title"],
                    doc_type=doc_data["doc_type"],
                    category=doc_data["category"],
                )

                # Create KnowledgeDoc record
                doc = KnowledgeDoc(
                    tenant_id=tenant_id,
                    title=doc_data["title"],
                    doc_type=doc_data["doc_type"],
                    category=doc_data["category"],
                    source=doc_key,
                    content=doc_data["content"].strip(),
                    extra_data=doc_data.get("metadata") or _build_metadata(doc_data),
                    version=1,
                )
                session.add(doc)
                await session.flush()

                # Process chunks
                chunks = processor.process(parsed)

                # Generate embeddings and store
                if chunks:
                    chunk_texts = [c["content"] for c in chunks]
                    embeddings = await embedding_service.aembed_batch(chunk_texts)

                    # Enrich chunk metadata with doc info, then pass directly to VectorStore
                    for c in chunks:
                        c["metadata"] = {
                            "doc_type": doc_data["doc_type"],
                            "category": doc_data["category"],
                            **(c.get("metadata") or {}),
                        }

                    await vector_store.add_vectors(
                        session=session,
                        doc_id=doc.id,
                        chunks=chunks,
                        embeddings=embeddings,
                        tenant_id=tenant_id,
                    )

                    total_chunks += len(chunks)
                    print(f"  → {len(chunks)} chunks embedded")

                await session.commit()
                success_count += 1
                print(f"  [OK] Done")

            except Exception as e:
                error_count += 1
                print(f"  [FAIL] Error: {e}")
                await session.rollback()

    print(f"\n{'='*50}")
    print(f"Knowledge Base Seed Complete!")
    print(f"  Documents: {success_count} created ({error_count} errors)")
    print(f"  Total Chunks: {total_chunks}")
    print(f"{'='*50}")

    # Verify
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT doc_type, count(*) FROM knowledge_docs WHERE tenant_id = :tid GROUP BY doc_type"),
            {"tid": tenant_id},
        )
        print("\nVerification:")
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]} docs")

        result2 = await session.execute(
            text("SELECT count(*) FROM knowledge_chunks WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )
        chunk_count = result2.scalar()
        print(f"  Total chunks: {chunk_count}")


if __name__ == "__main__":
    asyncio.run(main())
