"""
Multi-Agent E-Commerce Recommendation System — FastAPI Entry Point

Endpoints:
  POST /api/v1/recommend          - 获取个性化推荐
  POST /api/v1/recommend/graph    - 通过LangGraph pipeline推荐
  GET  /api/v1/experiments        - 查看A/B实验状态
  GET  /api/v1/metrics            - 查看系统监控指标
  GET  /health                    - 健康检查
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models.schemas import RecommendationRequest, RecommendationResponse
from orchestrator.supervisor import SupervisorOrchestrator
from orchestrator.graph import build_recommendation_graph
from services.ab_test import ABTestEngine
from services.metrics import MetricsCollector
from services.vector_store import MilvusVectorStore

logger = structlog.get_logger()
settings = get_settings()


ab_engine = ABTestEngine()
metrics_collector = MetricsCollector()
vector_store = MilvusVectorStore()  # 向量存储实例
supervisor = SupervisorOrchestrator(ab_engine=ab_engine, vector_store=vector_store)
rec_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rec_graph
    rec_graph = build_recommendation_graph()
    logger.info("app.startup", model=settings.llm_model)
    
    # 尝试连接向量存储 (非阻塞，失败则降级到 Mock 数据)
    try:
        if vector_store.connect():
            logger.info("vector_store.connected")
            # 启用向量检索
            supervisor.product_rec_agent._use_vector_store = True
            # 写入 Mock 商品数据
            from agents.product_rec_agent import MOCK_PRODUCTS
            count = await vector_store.upsert_products(MOCK_PRODUCTS)
            logger.info("vector_store.products_loaded", count=count)
        else:
            logger.warning("vector_store.connection_failed, using mock data")
    except Exception as e:
        logger.warning("vector_store.init_failed", error=str(e))
    
    yield
    
    # 清理资源
    vector_store.disconnect()
    logger.info("app.shutdown")


app = FastAPI(
    title="Multi-Agent E-Commerce Recommendation System",
    description="用户画像Agent + 商品推荐Agent + 营销文案Agent + 库存决策Agent，并行+聚合模式",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "model": settings.llm_model}


@app.post("/api/v1/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest):
    """使用Supervisor编排器进行推荐 (生产推荐用法)"""
    response = await supervisor.recommend(request)
    _collect_metrics(response)
    return response


@app.post("/api/v1/recommend/graph")
async def recommend_via_graph(request: RecommendationRequest):
    """使用LangGraph状态图进行推荐 (展示LangGraph能力)"""
    if not rec_graph:
        return {"error": "Graph not initialized"}
    state = {
        "user_id": request.user_id,
        "scene": request.scene,
        "num_items": request.num_items,
        "context": request.context,
    }
    result = await rec_graph.ainvoke(state)
    return {
        "request_id": result.get("request_id"),
        "user_id": result.get("user_id"),
        "products": [p.model_dump() for p in result.get("final_products", [])],
        "marketing_copies": result.get("marketing_copies", []),
        "experiment_group": result.get("experiment_group", "control"),
        "total_latency_ms": round(result.get("total_latency_ms", 0), 1),
    }


@app.get("/api/v1/experiments")
async def get_experiments():
    """查看所有A/B实验状态"""
    experiments = {}
    for exp_id, exp in ab_engine.experiments.items():
        experiments[exp_id] = {
            "name": exp.name,
            "enabled": exp.enabled,
            "groups": [
                {
                    "name": g.name,
                    "weight": g.weight,
                    "config": g.config,
                    "successes": g.successes,
                    "failures": g.failures,
                }
                for g in exp.groups
            ],
            "stats": ab_engine.get_stats(exp_id),
        }
    return experiments


@app.get("/api/v1/metrics")
async def get_metrics():
    """查看系统监控指标"""
    return {
        "agents": metrics_collector.get_agent_stats(),
        "business": metrics_collector.get_business_stats(),
    }


@app.post("/api/v1/experiments/{experiment_id}/outcome")
async def record_outcome(experiment_id: str, group: str, success: bool):
    """记录A/B测试结果,更新Thompson Sampling"""
    ab_engine.record_outcome(experiment_id, group, success)
    return {"status": "recorded"}


# ==================== Vector Store Endpoints ====================

@app.post("/api/v1/vector/connect")
async def connect_vector_store():
    """连接 Milvus 向量数据库"""
    success = vector_store.connect()
    if success:
        # 连接成功后，启用 ProductRecAgent 的向量检索
        supervisor.product_rec_agent._use_vector_store = True
    return {"connected": success, "stats": vector_store.get_stats()}


@app.post("/api/v1/vector/products")
async def upsert_products_to_vector():
    """
    将 Mock 商品数据写入向量数据库.
    
    生产环境中，应该从真实数据库读取商品并写入。
    """
    from agents.product_rec_agent import MOCK_PRODUCTS
    
    if not vector_store._connected:
        vector_store.connect()
    
    count = await vector_store.upsert_products(MOCK_PRODUCTS)
    return {"upserted": count, "total": len(MOCK_PRODUCTS)}


@app.get("/api/v1/vector/stats")
async def get_vector_stats():
    """获取向量存储统计信息"""
    return vector_store.get_stats()


def _collect_metrics(response: RecommendationResponse):
    for name, result in response.agent_results.items():
        metrics_collector.record_agent_call(
            agent_name=name,
            success=result.success,
            latency_ms=result.latency_ms,
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
