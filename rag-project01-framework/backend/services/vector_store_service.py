import os
from datetime import datetime
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
from pymilvus import connections, utility
from pymilvus import Collection, DataType, FieldSchema, CollectionSchema
from utils.config import VectorDBProvider, MILVUS_CONFIG  # Updated import
import re
import hashlib
from pypinyin import lazy_pinyin  # 需要安装：pip install pypinyin
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import chromadb
from chromadb.config import Settings

logger = logging.getLogger("services.vector_store")  # 使用层级化logger

def generate_milvus_name(original_name: str) -> str:
    """将包含空格/中文/特殊字符的文件名转换为合法的Milvus集合名称"""
    # 1. 统一处理空格：先转换为下划线
    original_name = original_name.replace(' ', '_')
    
    # 2. 中文转拼音
    if any('\u4e00' <= char <= '\u9fff' for char in original_name):
        original_name = '_'.join(lazy_pinyin(original_name))
    
    # 3. 替换所有非法字符
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', original_name)
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    
    # 4. 确保以字母开头
    if not cleaned or cleaned[0].isdigit():
        cleaned = 'col_' + cleaned
    
    # 5. 长度控制 (Milvus 2.x要求不超过255字符)
    if len(cleaned) > 255:
        prefix = cleaned[:200].rstrip('_')
        suffix = hashlib.md5(cleaned.encode()).hexdigest()[:8]
        cleaned = f"{prefix}_{suffix}"
    
    return cleaned.lower()  # Milvus 2.x要求小写

class VectorDBConfig:
    """
    向量数据库配置类，用于存储和管理向量数据库的配置信息
    """
    def __init__(
        self,
        provider: VectorDBProvider,
        index_mode: str,
        uri: str = None,
        index_types: Dict[str, str] = None,
        index_params: Dict[str, Dict[str, Any]] = None,
        persist_directory: str = None,
        collection_metadata: Dict[str, Any] = None
    ):
        """
        初始化向量数据库配置
        
        参数:
            provider: 向量数据库提供商名称
            index_mode: 索引模式
            uri: 数据库连接URI
            index_types: 索引类型字典
            index_params: 索引参数字典
            persist_directory: 持久化存储目录
            collection_metadata: 集合元数据
        """
        self.provider = provider
        self.index_mode = index_mode
        self.uri = uri
        self.index_types = index_types
        self.index_params = index_params
        self.persist_directory = persist_directory
        self.collection_metadata = collection_metadata

    def _get_milvus_index_type(self, index_mode: str) -> str:
        """
        根据索引模式获取Milvus索引类型
        
        参数:
            index_mode: 索引模式
            
        返回:
            对应的Milvus索引类型
        """
        return MILVUS_CONFIG["index_types"].get(index_mode, "FLAT")
    
    def _get_milvus_index_params(self, index_mode: str) -> Dict[str, Any]:
        """
        根据索引模式获取Milvus索引参数
        
        参数:
            index_mode: 索引模式
            
        返回:
            对应的Milvus索引参数字典
        """
        return MILVUS_CONFIG["index_params"].get(index_mode, {})

class VectorStoreService:
    """
    向量存储服务类，提供向量数据的索引、查询和管理功能
    """
    def __init__(self):
        """
        初始化向量存储服务
        """
        self.logger = logging.getLogger("services.vector_store.VectorStoreService")
        self.initialized_dbs = {}
        # 确保存储目录存在
        os.makedirs("03-vector-store", exist_ok=True)
        self.milvus_uri = "03-vector-store/langchain_milvus.db"
        self.chroma_client = chromadb.PersistentClient(
            path="03-vector-store/chroma_db"
        )
    
    def _get_milvus_index_type(self, config: VectorDBConfig) -> str:
        """
        从配置对象获取Milvus索引类型
        
        参数:
            config: 向量数据库配置对象
            
        返回:
            Milvus索引类型
        """
        return config._get_milvus_index_type(config.index_mode)
    
    def _get_milvus_index_params(self, config: VectorDBConfig) -> Dict[str, Any]:
        """
        从配置对象获取Milvus索引参数
        
        参数:
            config: 向量数据库配置对象
            
        返回:
            Milvus索引参数字典
        """
        return config._get_milvus_index_params(config.index_mode)
    
    def index_embeddings(self, embedding_file: str, config: VectorDBConfig) -> Dict[str, Any]:
        start_time = datetime.now()
        self.logger.info(f"开始索引流程 | 文件: {embedding_file} | 数据库: {config.provider} | 模式: {config.index_mode}")
        
        try:
            # 读取并验证文件
            try:
                self.logger.debug("开始加载和验证嵌入文件...")
                embeddings_data = self._load_embeddings(embedding_file)
                self.logger.debug(f"文件验证完成 | embeddings数量: {len(embeddings_data['embeddings'])}")
            except Exception as e:
                self.logger.error(f"文件加载/验证失败: {str(e)}", exc_info=True)
                raise

            # 执行索引
            result = {}
            if config.provider == VectorDBProvider.MILVUS:
                self.logger.debug("开始Milvus索引流程...")
                result = self._index_to_milvus(embeddings_data, config)
                self.logger.info(f"Milvus索引完成 | 集合名称: {result.get('collection_name')}")
            elif config.provider == VectorDBProvider.CHROMA:
                self.logger.debug("开始Chroma索引流程...")
                result = self._index_to_chroma(embeddings_data, config)
                self.logger.info(f"Chroma索引完成 | 集合名称: {result.get('collection_name')}")
            else:
                raise ValueError(f"Unsupported vector database provider: {config.provider}")
            
            processing_time = round((datetime.now() - start_time).total_seconds(), 2)
            self.logger.info(f"索引流程成功完成 | 耗时: {processing_time}s")
            
            return {
                "database": config.provider,
                "collection_name": result.get("collection_name", ""),
                "total_vectors": len(embeddings_data["embeddings"]),
                "index_size": result.get("index_size", 0),
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.logger.error(f"索引流程失败 | 错误: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=str(e),
                headers={"X-Error-Type": "indexing_error"}
            )
    
    def _load_embeddings(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 修正后的日志输出
            self.logger.debug(
                "文件验证 - 关键字段: \n"
                f"  embeddings: {bool(data.get('embeddings'))}\n"
                f"  vector_dimension: {data.get('vector_dimension')}\n"
                f"  embedding_provider: {data.get('embedding_provider')}"
            )
            
            # 验证必须字段
            required_fields = {
                'embeddings': {
                    'type': list,
                    'check': lambda x: len(x) > 0, 
                    'error': '必须是非空数组'
                },
                'vector_dimension': {
                    'type': (int, float),
                    'check': lambda x: x > 0,
                    'error': '必须是正数'
                },
                'embedding_provider': {
                    'type': str,
                    'check': lambda x: bool(x.strip()),
                    'error': '不能为空字符串'
                }
            }
            
            for field, config in required_fields.items():
                if field not in data:
                    raise ValueError(f"缺少必填字段: {field}")
                if not isinstance(data[field], config['type']):
                    raise ValueError(f"字段'{field}'类型错误: {config['error']}")
                if not config['check'](data[field]):
                    raise ValueError(f"字段'{field}'验证失败: {config['error']}")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {file_path}", exc_info=True)
            raise ValueError(f"无效的JSON格式: {str(e)}")
        except Exception as e:
            self.logger.error(f"文件验证失败: {file_path}", exc_info=True)
            raise
    
    def _index_to_milvus(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到Milvus数据库
        
        参数:
            embeddings_data: 嵌入向量数据
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        try:
            self.logger.debug("开始Milvus索引准备...")
            
            # 1. 验证必要字段
            required_fields = ["embeddings", "vector_dimension", "embedding_provider"]
            for field in required_fields:
                if field not in embeddings_data:
                    self.logger.error(f"Milvus索引缺少必要字段: {field}")
                    raise ValueError(f"Missing required field: {field}")
            
            # 2. 生成集合名称
            filename = embeddings_data.get("filename", "")
            base_name = Path(filename).stem if filename else "doc"
            embedding_provider = embeddings_data["embedding_provider"]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            raw_name = f"{base_name}_{embedding_provider}_{timestamp}"
            collection_name = generate_milvus_name(raw_name)
            
            self.logger.debug(f"生成集合名称 | 原始名称: {raw_name} → 转换后: {collection_name}")
            
            # 3. 验证向量维度
            vector_dim = int(embeddings_data["vector_dimension"])
            if vector_dim <= 0:
                self.logger.error(f"无效的向量维度: {vector_dim}")
                raise ValueError(f"Invalid vector dimension: {vector_dim}")
            
            # 4. 验证名称合法性 - 使用新的验证方式
            try:
                from pymilvus import utility
                # 新版本验证方式
                if hasattr(utility, 'check_collection_name'):
                    if not utility.check_collection_name(collection_name):
                        raise ValueError(f"Invalid collection name: {collection_name}")
                else:
                    # 兼容旧版本，使用正则表达式验证
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,255}$', collection_name):
                        raise ValueError(f"Invalid collection name: {collection_name}")
            except Exception as e:
                self.logger.error(f"集合名称验证失败: {str(e)}")
                raise ValueError(f"集合名称不合法: {collection_name}")
            
            # 5. 连接到Milvus
            connections.connect(
                alias="default", 
                uri=config.uri
            )
            
            self.logger.info(f"Creating collection with dimension: {vector_dim}")
            
            # 6. 定义字段
            fields = [
                {"name": "id", "dtype": "INT64", "is_primary": True, "auto_id": True},
                {"name": "content", "dtype": "VARCHAR", "max_length": 5000},
                {"name": "document_name", "dtype": "VARCHAR", "max_length": 255},
                {"name": "chunk_id", "dtype": "INT64"},
                {"name": "total_chunks", "dtype": "INT64"},
                {"name": "word_count", "dtype": "INT64"},
                {"name": "page_number", "dtype": "VARCHAR", "max_length": 10},
                {"name": "page_range", "dtype": "VARCHAR", "max_length": 10},
                # {"name": "chunking_method", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_provider", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_model", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_timestamp", "dtype": "VARCHAR", "max_length": 50},
                {
                    "name": "vector",
                    "dtype": "FLOAT_VECTOR",
                    "dim": vector_dim,
                    "params": self._get_milvus_index_params(config)
                }
            ]
            
            # 7. 准备数据为列表格式
            entities = []
            for emb in embeddings_data["embeddings"]:
                entity = {
                    "content": str(emb["metadata"].get("content", "")),
                    "document_name": embeddings_data.get("filename", ""),  # 使用 filename 而不是 document_name
                    "chunk_id": int(emb["metadata"].get("chunk_id", 0)),
                    "total_chunks": int(emb["metadata"].get("total_chunks", 0)),
                    "word_count": int(emb["metadata"].get("word_count", 0)),
                    "page_number": str(emb["metadata"].get("page_number", 0)),
                    "page_range": str(emb["metadata"].get("page_range", "")),
                    # "chunking_method": str(emb["metadata"].get("chunking_method", "")),
                    "embedding_provider": embeddings_data.get("embedding_provider", ""),  # 从顶层配置获取
                    "embedding_model": embeddings_data.get("embedding_model", ""),  # 从顶层配置获取
                    "embedding_timestamp": str(emb["metadata"].get("embedding_timestamp", "")),
                    "vector": [float(x) for x in emb.get("embedding", [])]
                }
                entities.append(entity)
            
            self.logger.info(f"Creating Milvus collection: {collection_name}")
            
            # 8. 创建collection
            field_schemas = []
            for field in fields:
                extra_params = {}
                if field.get('max_length') is not None:
                    extra_params['max_length'] = field['max_length']
                if field.get('dim') is not None:
                    extra_params['dim'] = field['dim']
                if field.get('params') is not None:
                    extra_params['params'] = field['params']
                field_schema = FieldSchema(
                    name=field["name"], 
                    dtype=getattr(DataType, field["dtype"]),
                    is_primary=field.get("is_primary", False),
                    auto_id=field.get("auto_id", False),
                    **extra_params
                )
                field_schemas.append(field_schema)

            schema = CollectionSchema(fields=field_schemas, description=f"Collection for {collection_name}")
            collection = Collection(name=collection_name, schema=schema)
            
            # 9. 插入数据
            self.logger.info(f"Inserting {len(entities)} vectors")
            insert_result = collection.insert(entities)
            
            # 10. 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": self._get_milvus_index_type(config),
                "params": self._get_milvus_index_params(config)
            }
            collection.create_index(field_name="vector", index_params=index_params)
            collection.load()
            
            self.logger.info(f"Milvus索引成功 | 集合: {collection_name} | 向量数: {len(embeddings_data['embeddings'])}")
            
            return {
                "index_size": len(insert_result.primary_keys),
                "collection_name": collection_name
            }
            
        except Exception as e:
            self.logger.error(f"Milvus索引过程中出错: {str(e)}", exc_info=True)
            raise
        
        finally:
            connections.disconnect("default")

    def _index_to_chroma(self, data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        collection_name = os.path.splitext(os.path.basename(data["filename"]))[0]
        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata=config.collection_metadata
        )

        documents = []
        metadatas = []
        ids = []
        embeddings = []

        for i, chunk in enumerate(data["chunks"]):
            documents.append(chunk["text"])
            metadatas.append({
                "source": data["filename"],
                "page": chunk.get("page_number", 0),
                "chunk_id": i,
                "total_chunks": len(data["chunks"])
            })
            ids.append(str(i))
            embeddings.append(chunk["embedding"])

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

        return {
            "status": "success",
            "collection_name": collection_name,
            "num_embeddings": len(embeddings)
        }

    def list_collections(self, provider: str) -> List[str]:
        """
        列出指定提供商的所有集合
        
        参数:
            provider: 向量数据库提供商
            
        返回:
            集合名称列表
        """
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                collections = utility.list_collections()
                return collections
            finally:
                connections.disconnect("default")
        return []

    def delete_collection(self, provider: str, collection_name: str) -> bool:
        """
        删除指定的集合
        
        参数:
            provider: 向量数据库提供商
            collection_name: 集合名称
            
        返回:
            是否删除成功
        """
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                utility.drop_collection(collection_name)
                return True
            finally:
                connections.disconnect("default")
        return False

    def get_collection_info(self, provider: str, collection_name: str) -> Dict[str, Any]:
        """
        获取指定集合的信息
        
        参数:
            provider: 向量数据库提供商
            collection_name: 集合名称
            
        返回:
            集合信息字典
        """
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                collection = Collection(collection_name)
                return {
                    "name": collection_name,
                    "num_entities": collection.num_entities,
                    "schema": collection.schema.to_dict()
                }
            finally:
                connections.disconnect("default")
        return {}