import os
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

class OpenAIText2SQL:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化OpenAI模型
        
        Args:
            config: 模型配置字典，包含以下字段：
                - model: 模型名称
                - api_key: OpenAI API密钥
                - temperature: 生成温度
        """
        self.model = config.get('model', 'gpt-4')
        self.temperature = config.get('temperature', 0.1)
        
        # 获取API密钥
        api_key = config.get('api_key')
        if not api_key:
            load_dotenv('/home/gssnet/rag-in-action/.env')
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API密钥未设置")
                
        self.client = OpenAI(api_key=api_key)
        
    def generate_sql(self, question: str, schema_info: str) -> str:
        """
        生成SQL查询
        
        Args:
            question: 自然语言问题
            schema_info: 数据库模式信息
            
        Returns:
            生成的SQL查询
        """
        # 构建提示
        prompt = f"""数据库模式信息：
{schema_info}

问题：{question}

请生成对应的SQL查询："""
        
        # 调用API生成SQL
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的SQL专家，请根据给定的数据库模式信息和问题生成对应的SQL查询。"},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )
        
        # 提取SQL
        sql = response.choices[0].message.content.strip()
        return sql 