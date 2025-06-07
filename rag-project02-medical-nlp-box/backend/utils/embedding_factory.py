import sys
import os
from typing import List, Optional, Dict, Any

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .embedding_config import EmbeddingProvider, EmbeddingConfig
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings.base import Embeddings
import boto3
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingFactory:
    """
    嵌入模型工厂类
    用于创建不同类型的嵌入模型实例
    """
    @staticmethod
    def create_embedding_function(config: EmbeddingConfig) -> Embeddings:
        """
        根据配置创建对应的 embedding 函数
        
        Args:
            config: EmbeddingConfig 对象，包含 provider 和 model_name
            
        Returns:
            Embeddings 对象
        """
        if config.provider == EmbeddingProvider.HUGGINGFACE:
            return HuggingFaceEmbeddings(
                model_name=config.model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        elif config.provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbeddings(
                model=config.model_name,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
        elif config.provider == EmbeddingProvider.BEDROCK:
            # 创建 Bedrock 客户端
            bedrock = boto3.client(
                service_name='bedrock-runtime',
                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            # 创建自定义的 Bedrock 嵌入函数
            def bedrock_embedding(text: str) -> list:
                """
                使用 Bedrock 生成文本嵌入
                
                Args:
                    text: 输入文本
                    
                Returns:
                    文本的向量表示
                """
                try:
                    response = bedrock.invoke_model(
                        modelId=config.model_name,
                        body=json.dumps({
                            "inputText": text
                        })
                    )
                    response_body = json.loads(response.get('body').read())
                    return response_body.get('embedding', [])
                except Exception as e:
                    logger.error(f"Error generating embedding with Bedrock: {str(e)}")
                    raise
                    
            return bedrock_embedding
        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")