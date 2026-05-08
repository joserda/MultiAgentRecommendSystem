# 🛒 多Agent电商推荐与营销系统

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](python/)
[![Vue](https://img.shields.io/badge/Vue-3.4%2B-4FC08D?logo=vue.js)](vue/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

***

## 📖 目录

1. [这个项目是什么？](#-这个项目是什么)
2. [系统架构（看图秒懂）](#-系统架构看图秒懂)
3. [四大核心 Agent 详解](#-四大核心-agent-详解)
4. [技术栈说明](#-技术栈说明)
5. [关键代码展示](#-关键代码展示)
6. [快速上手运行](#-快速上手运行)
7. [API 接口文档](#-api-接口文档)
8. [项目文件结构](#-项目文件结构)
9. [面试资料索引](#-面试资料索引)
10. [面试八股文精选](#-面试八股文精选10题)
11. [简历写法（直接复制）](#-简历写法直接复制)
12. [参考资料与致谢](#-参考资料与致谢)

***

## 🤔 这个项目是什么？

### 用一句话解释

> 用 AI Agent 技术，让电商平台的**推荐 + 文案 + 库存**三个系统协同工作，像一个聪明的"AI 运营团队"一起为每位用户生成个性化推荐结果。

### 它解决了什么问题？

传统电商推荐系统存在三大痛点：

| 痛点        | 传统做法             | 本项目做法                        |
| --------- | ---------------- | ---------------------------- |
| 推荐结果和库存脱节 | 推荐了缺货商品          | **库存 Agent** 实时校验，缺货自动剔除     |
| 营销文案千篇一律  | 所有人看同一段广告语       | **文案 Agent** 根据用户画像生成个性化文案   |
| 各系统各自为战   | 推荐、文案、库存三套系统互不感知 | **Supervisor** 统一编排，结果实时互相影响 |

### 技术关键词（面试常考）

`Multi-Agent` · `Supervisor模式` · `LangGraph` · `asyncio并行` · `Redis Feature Store` · `A/B Testing` · `Thompson Sampling` · `RAG` · `ReAct` · `MiniMax LLM`

***

## 🏗 系统架构（看图秒懂）

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户发起推荐请求                           │
│                    {"user_id": "u001", "num_items": 5}           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supervisor 协调Agent                           │
│                  (python/orchestrator/supervisor.py)              │
│                                                                   │
│  ════════════════ Phase 1: 并行执行 ═══════════════════           │
│  ┌──────────────────────┐    ┌──────────────────────┐            │
│  │   用户画像 Agent      │    │   商品召回 Agent      │            │
│  │  user_profile_agent  │    │  product_rec_agent   │            │
│  │  ──────────────────  │    │  ────────────────── │            │
│  │  Redis → 实时行为特征 │    │  协同过滤+向量检索召回 │            │
│  │  RFM模型 → 用户分群   │    │  返回候选商品列表     │            │
│  └──────────┬───────────┘    └──────────┬──────────┘            │
│             │                           │                         │
│  ════════════════ Phase 2: 并行执行 ═══════════════════           │
│  ┌──────────────────────┐    ┌──────────────────────┐            │
│  │   LLM重排 Agent      │    │   库存决策 Agent      │            │
│  │  (product_rec再次调用)│    │   inventory_agent    │            │
│  │  ──────────────────  │    │  ────────────────── │            │
│  │  用户画像 × 商品属性  │    │  MySQL → 实时库存查询 │            │
│  │  LLM精排，返回TopN   │    │  过滤缺货，输出限购策略│            │
│  └──────────┬───────────┘    └──────────┬──────────┘            │
│             │                           │                         │
│  ════════════════ Phase 3: 串行执行 ═══════════════════           │
│             └──────────────┬────────────┘                         │
│                            ▼                                      │
│             ┌──────────────────────────────┐                      │
│             │      结果聚合器               │                      │
│             │  库存过滤 → 排序合并 → TopN   │                      │
│             └──────────────┬───────────────┘                      │
│                            ▼                                      │
│             ┌──────────────────────────────┐                      │
│             │   营销文案 Agent              │                      │
│             │  marketing_copy_agent        │                      │
│             │  ────────────────────────── │                      │
│             │  5套Prompt模板 × 用户分群    │                      │
│             │  LLM生成 + 广告法合规校验    │                      │
│             └──────────────┬───────────────┘                      │
│                            ▼                                      │
│             ┌──────────────────────────────┐                      │
│             │   A/B 测试引擎               │                      │
│             │  用户ID哈希分桶              │                      │
│             │  Thompson Sampling 动态调优  │                      │
│             └──────────────┬───────────────┘                      │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
              ┌─────────────────────────────────┐
              │  个性化推荐响应（返回给用户）      │
              │  商品列表 + 个性化文案 + 实验分组 │
              └─────────────────────────────────┘
```

### 为什么用 Supervisor 模式？

Supervisor 模式是 Multi-Agent 系统中最主流的编排方式之一：

```
Supervisor 模式                     Handoffs 模式
──────────────────────              ──────────────────────
   Supervisor（中枢）                 Agent A → Agent B
    ┌────┬────┬────┐                       ↓
    ▼    ▼    ▼    ▼                 Agent B → Agent C
   A    B    C    D                        ↓
    └────┴────┴────┘                 Agent C → ...
    结果聚合 → 响应

✅ 集中控制，流程清晰          ✅ 去中心化，灵活
✅ 并行执行，延迟低            ✅ 适合对话/开放式任务
✅ 异常统一处理                ❌ 状态管理复杂
本项目采用 Supervisor 模式
```

***

## 🤖 四大核心 Agent 详解

### Agent 1：用户画像 Agent

**文件**：[`python/agents/user_profile_agent.py`](python/agents/user_profile_agent.py)

**它做什么？**

把用户的历史行为数据（点击、购买、收藏）转化成结构化的"用户画像"，供其他 Agent 使用。

**核心逻辑（简化）**：

```python
# Step 1：从 Redis Feature Store 获取实时行为特征
behavior = await feature_store.get_user_features(user_id)
# 返回: {"clicks_1h": 12, "purchases_7d": 3, "categories": ["手机", "耳机"]}

# Step 2：调用 LLM 分析，输出结构化画像
prompt = f"用户行为数据: {behavior}\n请分析用户分群和RFM得分，输出JSON"
profile_json = await llm.invoke(prompt)
# 输出: {"segments": ["active", "price_sensitive"], "rfm_score": {"recency": 0.8}}

# Step 3：返回 UserProfile 对象
return UserProfile(user_id=user_id, segments=["active"], rfm_score=...)
```

**关键技术**：

- **Redis Sorted Set**：`ZADD user:u001:clicks {时间戳} {商品ID}`，支持滑动窗口查询
- **RFM 模型**：Recency（最近购买时间）× Frequency（购买频率）× Monetary（消费金额）
- **用户分群**：新客 / VIP / 价格敏感 / 活跃 / 流失风险，共 5 类

***

### Agent 2：商品推荐 Agent

**文件**：[`python/agents/product_rec_agent.py`](python/agents/product_rec_agent.py)

**它做什么？**

两阶段推荐：先"召回"大量候选商品，再用 LLM 精排出最合适的 TopN。

```
多路召回策略
  ├── 协同过滤（买了A也买了B）
  ├── 向量检索（Milvus，语义相似商品）
  ├── 热度策略（最近7天热卖）
  └── 新品策略（上架30天内）
        │
        ▼（去重合并，候选集）
  LLM 精排
  │ Prompt: "用户是价格敏感型，偏好手机配件，以下10件商品请排序..."
  │ 输出: 按相关性从高到低排列的商品 ID 列表
        │
        ▼
  TopN 商品列表（交给库存 Agent 过滤）
```

***

### Agent 3：营销文案 Agent

**文件**：[`python/agents/marketing_copy_agent.py`](python/agents/marketing_copy_agent.py)

**它做什么？**

根据用户画像自动选择合适的文案风格模板，调用 LLM 生成个性化文案，并做广告法合规校验。

```python
# 5套模板 × 用户分群
TEMPLATES = {
    "new_user":        "首单专属福利，{product}立减{discount}元！",
    "vip":             "尊享会员特权，{product}专属价{price}，品质之选。",
    "price_sensitive": "今日限时抢购！{product}历史最低价，仅剩{stock}件！",
    "active":          "根据您的浏览偏好，为您精选 {product}，好评率{rating}%",
    "churn_risk":      "好久不见！{product}为您专属保留，点击领取优惠券",
}

# 广告法合规校验（过滤违禁词）
BANNED_WORDS = ["最好", "第一", "最便宜", "绝对", "100%"]
```

***

### Agent 4：库存决策 Agent

**文件**：[`python/agents/inventory_agent.py`](python/agents/inventory_agent.py)

**它做什么？**

查询商品实时库存，过滤缺货商品，输出限购策略和补货预警。

```python
# 输入: 推荐商品列表 [P001, P002, P003, ...]
# 查询 MySQL/WMS 实时库存
# 输出:
{
    "available_products": ["P001", "P003"],   # 有货商品
    "inventory_alerts": [                      # 库存预警
        {"product_id": "P001", "stock": 5, "warning": "库存紧张"}
    ],
    "purchase_limits": {                       # 限购策略
        "P001": 2  # 每人最多买2件
    }
}
```

***

## 🌐 技术栈说明

### 后端技术栈

| 组件    | 技术选型                 | 说明             |
| ----- | -------------------- | -------------- |
| 框架    | LangGraph + FastAPI  | 生产级Agent编排框架   |
| 并行方式  | `asyncio.gather()`   | Python原生异步并行   |
| LLM   | MiniMax M2.7         | 通过OpenAI兼容接口调用 |
| 向量数据库 | Milvus               | 商品向量检索         |
| 特征存储  | Redis                | 实时用户特征         |
| 业务数据  | SQLite/MySQL         | 商品、库存数据        |
| 代码位置  | [`python/`](python/) | Python后端实现     |

### 前端技术栈

| 组件      | 技术选型           | 说明      |
| ------- | -------------- | ------- |
| 框架      | Vue 3          | 现代化前端框架 |
| 构建工具    | Vite           | 快速开发构建  |
| HTTP客户端 | Axios          | API请求   |
| 代码位置    | [`vue/`](vue/) | Vue前端实现 |

***

## 💻 关键代码展示

### Supervisor 并行编排（Python 核心代码）

**文件**：[`python/orchestrator/supervisor.py`](python/orchestrator/supervisor.py)

```python
class SupervisorOrchestrator:
    """Supervisor 编排器 — 并行分发 + 聚合模式"""

    async def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        start = time.perf_counter()

        # ① A/B 实验分组（在最开始就决定用哪套策略）
        experiment = self.ab_engine.assign(request.user_id)

        # ② Phase 1：用户画像 + 商品召回 并行执行
        profile_result, rec_result = await asyncio.gather(
            self.user_profile_agent.run(user_id=request.user_id, context=request.context),
            self.product_rec_agent.run(user_profile=None, num_items=request.num_items * 2),
        )
        # asyncio.gather() 让两个 IO 密集型任务同时跑，总耗时 ≈ max(两者耗时)

        # ③ Phase 2：LLM重排 + 库存校验 并行执行
        rerank_result, inventory_result = await asyncio.gather(
            self.product_rec_agent.run(user_profile=user_profile, num_items=request.num_items),
            self.inventory_agent.run(products=raw_products),
        )

        # ④ 库存过滤：只保留有货商品
        available_ids = set(getattr(inventory_result, "available_products", []))
        final_products = [p for p in ranked_products if p.product_id in available_ids]

        # ⑤ Phase 3：文案生成（需要前两步结果，所以串行）
        copy_result = await self.marketing_copy_agent.run(
            user_profile=user_profile,
            products=final_products,
        )

        # ⑥ 汇总响应
        total_latency = (time.perf_counter() - start) * 1000
        return RecommendationResponse(
            products=final_products,
            marketing_copies=copies,
            experiment_group=experiment.get("group", "control"),
            total_latency_ms=total_latency,  # 目标 P99 < 2000ms
        )
```

> 💡 **小白解读**：`asyncio.gather()` 就像你同时开了两个网页，而不是等一个加载完再开另一个。两个 Agent 并行跑，总延迟约等于最慢那个 Agent 的耗时，而不是两者相加。

***

### A/B 测试引擎（Thompson Sampling）

**文件**：[`python/services/ab_test.py`](python/services/ab_test.py)

```python
class ABTestEngine:
    """
    流量分桶 + Thompson Sampling 多臂赌博机
    
    原理：像赌场里的老虎机，哪台赢的多就多拉哪台。
    算法自动把更多流量分给表现好的实验组。
    """

    def assign(self, user_id: str) -> dict:
        # 用户ID哈希取模 → 保证同一用户每次进同一个实验组（一致性）
        bucket = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
        
        if bucket < 60:
            return {"group": "control", "strategy": "collaborative_filter"}
        elif bucket < 80:
            return {"group": "treatment_llm", "strategy": "llm_rerank"}
        else:
            return {"group": "treatment_vector", "strategy": "vector_search"}

    def record_click(self, user_id: str, clicked: bool):
        # Thompson Sampling: 点击了就更新 Beta 分布参数
        group = self.assignments.get(user_id, "control")
        if clicked:
            self.alpha[group] += 1   # 成功次数 +1
        else:
            self.beta[group] += 1    # 失败次数 +1
        # 下次分配流量时，胜率高的组会自动获得更多流量
```

***

### Agent 基类：重试 + 降级（可靠性保障）

**文件**：[`python/agents/base_agent.py`](python/agents/base_agent.py)

```python
class BaseAgent(ABC):
    """所有 Agent 的基类 — 模板方法模式"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒，指数退避

    async def run(self, **kwargs) -> AgentResult:
        """公开方法：封装了计时、重试、降级"""
        start = time.perf_counter()
        try:
            return await self._retry_execute(**kwargs)
        except Exception as e:
            # 全部重试失败 → 降级（返回默认结果，不影响其他 Agent）
            logger.warning(f"{self.name} fallback triggered: {e}")
            return self._fallback(**kwargs)

    async def _retry_execute(self, **kwargs) -> AgentResult:
        """指数退避重试"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return await asyncio.wait_for(
                    self._execute(**kwargs),
                    timeout=self.timeout,  # 每个 Agent 独立超时控制
                )
            except asyncio.TimeoutError:
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (2 ** attempt))  # 1s, 2s, 4s
        raise RuntimeError(f"{self.name} failed after {self.MAX_RETRIES} retries")

    @abstractmethod
    async def _execute(self, **kwargs) -> AgentResult:
        """子类只需实现这个方法，写业务逻辑即可"""
```

> 💡 **小白解读**：就像打电话打不通会重拨，第1次立刻重拨，第2次等2秒，第3次等4秒（指数退避）。如果全失败了，就返回一个"说得过去的默认结果"（降级），保证整个系统不崩溃。

***

## 🚀 快速上手运行

### 前置条件

- Python 3.11+
- Node.js 16+（用于前端）
- 申请 LLM API Key（推荐 [MiniMax](https://www.minimax.chat/) 或 [阿里通义](https://dashscope.aliyun.com/)，有免费额度）

***

### 后端启动（Python）

```bash
# 1. 克隆项目
git clone https://github.com/bcefghj/multi-agent-ecommerce-system.git
cd multi-agent-ecommerce-system/python

# 2. 创建虚拟环境（避免依赖冲突）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
cp .env.example .env
# 用记事本/VS Code 打开 .env，填入你的 LLM_API_KEY

# 5. 启动服务
python main.py
# 看到 "Uvicorn running on http://0.0.0.0:8000" 就成功了

# 6. 测试推荐接口
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u001", "num_items": 5}'
```

***

### 前端启动（Vue）

```bash
# 1. 进入前端目录
cd multi-agent-ecommerce-system/vue

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
# 访问 http://localhost:5173

# 4. 构建生产版本
npm run build
```

***

### Docker 一键部署

```bash
# 启动所有服务（Redis + Milvus + MySQL + Python API + Vue前端）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

***

## 📡 API 接口文档

### 1. 获取个性化推荐

**POST** `/api/v1/recommend`

**请求体**：

```json
{
  "user_id": "u001",
  "num_items": 5,
  "context": {
    "session_id": "s123",
    "platform": "mobile"
  }
}
```

**响应**：

```json
{
  "products": [
    {
      "product_id": "P001",
      "name": "无线蓝牙耳机",
      "price": 299.0,
      "category": "数码配件",
      "rating": 4.8,
      "stock": 150
    }
  ],
  "marketing_copies": [
    {
      "product_id": "P001",
      "copy": "根据您的浏览偏好，为您精选 无线蓝牙耳机，好评率4.8%"
    }
  ],
  "experiment_group": "treatment_llm",
  "total_latency_ms": 1250.5
}
```

***

### 2. 通过 LangGraph Pipeline 推荐

**POST** `/api/v1/recommend/graph`

使用 LangGraph 状态机编排的推荐流程，支持更复杂的流程控制。

***

### 3. 查看 A/B 实验状态

**GET** `/api/v1/experiments`

返回当前所有实验的统计数据。

***

### 4. 查看系统监控指标

**GET** `/api/v1/metrics`

返回系统性能指标，包括：

- Agent 调用延迟
- 成功率
- A/B 实验转化率

***

## 📁 项目文件结构

```
multi-agent-ecommerce-system/
├── README.md                      # 项目文档（本文件）
├── docker-compose.yml             # Docker编排配置
├── plan.md                        # 项目规划
├── .gitignore                     # Git忽略文件
│
├── docs/                          # 文档目录
│   ├── architecture.md            # 架构设计文档
│   ├── code-walkthrough.md        # 代码讲解
│   ├── interview-guide.md         # 面试指南
│   ├── project-plan.md            # 项目计划
│   └── resume-template.md         # 简历模板
│
├── python/                        # Python后端
│   ├── main.py                    # FastAPI入口
│   ├── requirements.txt           # Python依赖
│   ├── Dockerfile                 # Python Docker配置
│   │
│   ├── agents/                    # Agent实现
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Agent基类
│   │   ├── user_profile_agent.py  # 用户画像Agent
│   │   ├── product_rec_agent.py   # 商品推荐Agent
│   │   ├── marketing_copy_agent.py # 营销文案Agent
│   │   └── inventory_agent.py     # 库存决策Agent
│   │
│   ├── orchestrator/              # 编排层
│   │   ├── __init__.py
│   │   ├── supervisor.py          # Supervisor编排器
│   │   └── graph.py               # LangGraph状态图
│   │
│   ├── services/                  # 服务层
│   │   ├── __init__.py
│   │   ├── ab_test.py             # A/B测试引擎
│   │   ├── feature_store.py       # 特征存储
│   │   ├── metrics.py             # 监控指标
│   │   └── vector_store.py        # 向量存储
│   │
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic模型
│   │
│   ├── config/                    # 配置
│   │   ├── __init__.py
│   │   └── settings.py            # 配置管理
│   │
│   └── tests/                     # 测试
│       ├── __init__.py
│       └── test_ab_test.py        # A/B测试单元测试
│
└── vue/                           # Vue前端
    ├── index.html                 # HTML入口
    ├── package.json               # Node依赖
    ├── vite.config.js             # Vite配置
    │
    ├── public/                    # 静态资源
    │   └── favicon.svg
    │
    └── src/                       # 源代码
        ├── main.js                # Vue入口
        ├── App.vue                # 根组件
        ├── style.css              # 全局样式
        └── api/
            └── index.js           # API封装
```

***


## 🙏 参考资料与致谢

### 技术文档

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [MiniMax API 文档](https://www.minimax.chat/document/)
- [Milvus 向量数据库](https://milvus.io/docs/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)

### 参考项目

- [NVIDIA Retail Agentic Commerce](https://github.com/NVIDIA-AI-Blueprints/Retail-Agentic-Commerce)
- [Spring AI Alibaba Multi-Agent Demo](https://github.com/spring-ai-alibaba/spring-ai-alibaba-multi-agent-demo)
- [DualAgent-Rec](https://github.com/GuilinDev/Dual-Agent-Recommendation)

### 致谢

感谢以上开源项目和文档的作者，为本项目提供了宝贵的参考和灵感。

***

## 📄 License

本项目采用 MIT 协议开源，详见 [LICENSE](LICENSE) 文件。

***

<div align="center">

**⭐ 如果这个项目对你有帮助，欢迎 Star 支持！**

Made with ❤️ by \[Your Name]

</div>
