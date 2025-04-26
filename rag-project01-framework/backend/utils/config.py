from enum import Enum
from typing import Dict, Any

class VectorDBProvider(str, Enum):
    MILVUS = "milvus"
    CHROMA = "chroma"
    # More providers can be added later

# 可以在这里添加其他配置相关的内容
MILVUS_CONFIG = {
    "uri": "03-vector-store/langchain_milvus.db",
    "index_types": {
        "flat": "FLAT",
        "ivf_flat": "IVF_FLAT",
        "ivf_sq8": "IVF_SQ8",
        "hnsw": "HNSW"
    },
    "index_params": {
        "flat": {},
        "ivf_flat": {"nlist": 1024},
        "ivf_sq8": {"nlist": 1024},
        "hnsw": {
            "M": 16,
            "efConstruction": 500
        }
    }
}

CHROMA_CONFIG = {
    "persist_directory": "03-vector-store/chroma_db",
    "collection_metadata": {
        "hnsw:space": "cosine",  # 可选: "l2", "ip", "cosine"
        "hnsw:M": 16,  # 构建时的连接数
        "hnsw:ef_construction": 200,  # 构建时的搜索范围
        "hnsw:ef": 10  # 查询时的搜索范围
    }
} 