"""
Milvus 向量存储服务
- 商品向量入库：商品信息 → Ollama embedding → Milvus 存储
- 向量检索：用户偏好/查询 → embedding → ANN 检索
- 混合召回：向量检索 + 协同过滤 + 热门策略
"""

from __future__ import annotations

import asyncio
import structlog
from typing import Any

import httpx
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from config import get_settings
from models.schemas import Product

logger = structlog.get_logger()


class OllamaEmbedding:
    """Ollama 本地嵌入模型客户端 (nomic-embed-text)."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        # HTTP 客户端，设置合理超时
        self.client = httpx.AsyncClient(timeout=30.0)

    async def embed(self, text: str) -> list[float]:
        """生成单个文本的嵌入向量."""
        try:
            resp = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error("embedding.failed", text=text[:50], error=str(e))
            return []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入向量 (并发调用)."""
        tasks = [self.embed(t) for t in texts]
        return await asyncio.gather(*tasks)

    async def close(self):
        await self.client.aclose()


class MilvusVectorStore:
    """
    Milvus 向量数据库封装.
    
    Collection 结构:
        - product_id (VARCHAR): 商品唯一标识
        - name (VARCHAR): 商品名称
        - category (VARCHAR): 类目
        - price (FLOAT): 价格
        - embedding (FLOAT_VECTOR): 向量嵌入
    """

    def __init__(self):
        settings = get_settings()
        self.host = settings.milvus_host
        self.port = settings.milvus_port
        self.collection_name = settings.milvus_collection
        self.embedding_dim = settings.embedding_dim

        # 嵌入模型
        self.embedder = OllamaEmbedding(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
        )

        self._connected = False
        self._collection: Collection | None = None

    # ---------- 连接管理 ----------

    def connect(self) -> bool:
        """连接 Milvus 服务并初始化 Collection."""
        if self._connected:
            return True

        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )
            self._connected = True
            logger.info("milvus.connected", host=self.host, port=self.port)

            # 确保 collection 存在
            self._ensure_collection()
            return True
        except Exception as e:
            logger.error("milvus.connect_failed", error=str(e))
            return False

    def _ensure_collection(self):
        """创建 Collection (如不存在) 并加载到内存."""
        if utility.has_collection(self.collection_name):
            self._collection = Collection(self.collection_name)
        else:
            # 定义 schema
            fields = [
                FieldSchema(name="product_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="price", dtype=DataType.FLOAT),
                FieldSchema(name="stock", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            ]
            schema = CollectionSchema(fields=fields, description="商品向量索引")
            self._collection = Collection(name=self.collection_name, schema=schema)

            # 创建向量索引 (IVF_FLAT，适合中等规模数据)
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            self._collection.create_index(field_name="embedding", index_params=index_params)
            logger.info("milvus.collection_created", name=self.collection_name)

        # 加载到内存以支持搜索
        self._collection.load()

    def disconnect(self):
        """断开 Milvus 连接."""
        if self._connected:
            connections.disconnect("default")
            self._connected = False
            logger.info("milvus.disconnected")

    # ---------- 数据写入 ----------

    async def upsert_products(self, products: list[Product]) -> int:
        """
        批量写入/更新商品向量.
        
        流程: 商品信息 → 构建文本 → Ollama embedding → Milvus upsert
        """
        if not self._collection or not products:
            return 0

        # 1. 构建嵌入文本 (名称 + 类目 + 标签)
        texts = [
            f"{p.name} {p.category} {' '.join(p.tags)} {p.description[:100]}"
            for p in products
        ]

        # 2. 批量生成 embedding
        embeddings = await self.embedder.embed_batch(texts)

        # 3. 过滤无效向量
        valid_data = []
        for i, (product, emb) in enumerate(zip(products, embeddings)):
            if len(emb) != self.embedding_dim:
                logger.warning("embedding.invalid_dim", product_id=product.product_id)
                continue
            valid_data.append([
                product.product_id,
                product.name,
                product.category,
                product.price,
                product.stock,
                emb,
            ])

        if not valid_data:
            return 0

        # 4. 写入 Milvus (insert 会自动去重，因为 product_id 是主键)
        try:
            self._collection.insert(valid_data)
            self._collection.flush()
            logger.info("milvus.products_upserted", count=len(valid_data))
            return len(valid_data)
        except Exception as e:
            logger.error("milvus.upsert_failed", error=str(e))
            return 0

    # ---------- 向量检索 ----------

    async def search(
        self,
        query: str,
        top_k: int = 20,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        向量相似度检索.
        
        Args:
            query: 查询文本 (用户偏好描述 / 搜索词)
            top_k: 返回结果数量
            filter_expr: Milvus 过滤表达式，如 'category == "手机"'
        
        Returns:
            商品信息列表，包含 product_id, name, category, price, distance
        """
        if not self._collection:
            return []

        # 1. 查询文本向量化
        query_emb = await self.embedder.embed(query)
        if not query_emb:
            return []

        # 2. 执行 ANN 搜索
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        try:
            results = self._collection.search(
                data=[query_emb],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["product_id", "name", "category", "price", "stock"],
            )
        except Exception as e:
            logger.error("milvus.search_failed", query=query[:50], error=str(e))
            return []

        # 3. 解析结果
        hits = []
        for hit in results[0]:
            entity = hit.entity
            hits.append({
                "product_id": entity.get("product_id"),
                "name": entity.get("name"),
                "category": entity.get("category"),
                "price": entity.get("price"),
                "stock": entity.get("stock"),
                "distance": hit.distance,  # 余弦距离，越小越相似
                "score": 1.0 - hit.distance,  # 转换为相似度分数
            })
        return hits

    async def search_by_user_profile(
        self,
        preferred_categories: list[str],
        recent_views: list[str],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """
        基于用户画像的向量检索.
        
        策略:
            1. 构建用户偏好查询文本
            2. 优先检索偏好类目
            3. 结合最近浏览商品做扩展召回
        """
        # 1. 构建偏好查询
        query_parts = []
        if preferred_categories:
            query_parts.append(f"用户偏好类目: {' '.join(preferred_categories[:3])}")
        if recent_views:
            query_parts.append(f"最近浏览: {' '.join(recent_views[:5])}")

        if not query_parts:
            return []

        query = " ".join(query_parts)

        # 2. 主召回：偏好类目过滤
        all_hits = []
        if preferred_categories:
            # 按类目分别检索，保证多样性
            for cat in preferred_categories[:2]:
                filter_expr = f'category == "{cat}"'
                hits = await self.search(query, top_k=top_k // 2, filter_expr=filter_expr)
                all_hits.extend(hits)

        # 3. 补充召回：无过滤检索
        if len(all_hits) < top_k:
            extra_hits = await self.search(query, top_k=top_k)
            seen_ids = {h["product_id"] for h in all_hits}
            for h in extra_hits:
                if h["product_id"] not in seen_ids:
                    all_hits.append(h)
                    if len(all_hits) >= top_k:
                        break

        return all_hits[:top_k]

    # ---------- 统计信息 ----------

    def get_stats(self) -> dict[str, Any]:
        """获取 Collection 统计信息."""
        if not self._collection:
            return {}
        self._collection.flush()
        return {
            "collection": self.collection_name,
            "row_count": self._collection.num_entities,
            "connected": self._connected,
        }
