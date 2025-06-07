import pandas as pd
import numpy as np
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.embedding_factory import EmbeddingFactory
from backend.utils.embedding_config import EmbeddingProvider, EmbeddingConfig
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 连接 Milvus
connections.connect(
    alias="default",
    host="localhost",
    port="19530"
)

# 配置参数
collection_name = "financial_terms"
vector_dim = 1024  # BGE-m3 的维度
batch_size = 1024

# 创建 embedding 函数
config = EmbeddingConfig(
    provider=EmbeddingProvider.HUGGINGFACE,
    model_name="BAAI/bge-m3"
)
embedding_function = EmbeddingFactory.create_embedding_function(config)

# 读取金融术语数据
file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "万条金融标准术语.csv")
df = pd.read_csv(file_path, header=None, names=['term', 'type'])

# 构造Schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
    FieldSchema(name="term", dtype=DataType.VARCHAR, max_length=200),
    FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="input_file", dtype=DataType.VARCHAR, max_length=500),
]
schema = CollectionSchema(fields, 
                         "Financial Terms", 
                         enable_dynamic_field=True)

# 判断集合是否存在，如果存在则删除，然后创建新集合
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    logger.info(f"Dropped existing collection: {collection_name}")

collection = Collection(name=collection_name, schema=schema)
logger.info(f"Created new collection: {collection_name}")
# 创建索引
index_params = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}
collection.create_index(field_name="vector", index_params=index_params)
# 创建后立即加载集合
collection.load()
logger.info(f"Collection {collection_name} loaded after creation")

# 分批处理数据
total_rows = len(df)
for start_idx in range(0, total_rows, batch_size):
    end_idx = min(start_idx + batch_size, total_rows)
    batch_df = df.iloc[start_idx:end_idx]
    
    # 生成向量嵌入
    terms = batch_df['term'].tolist()
    embeddings = embedding_function.embed_documents(terms)
    
    # 准备数据
    data = [
        {
            "vector": embeddings[idx],
            "term": str(row['term']),
            "type": str(row['type']),
            "input_file": file_path
        } for idx, (_, row) in enumerate(batch_df.iterrows())
    ]
    
    # 插入数据
    try:
        res = collection.insert(data)
        logger.info(f"Inserted batch {start_idx // batch_size + 1}, result: {res}")
    except Exception as e:
        logger.error(f"Error inserting batch {start_idx // batch_size + 1}: {e}")

logger.info("Insert process completed.")

# 示例查询
query = "股票"
query_embedding = embedding_function.embed_query(query)

# 确保集合已加载
collection.load()
logger.info(f"Collection {collection_name} loaded before search")

# 搜索相似术语
search_result = collection.search(
    data=[query_embedding],
    anns_field="vector",
    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
    limit=5,
    output_fields=["term", "type"]
)

logger.info(f"Search result for '{query}': {search_result}") 