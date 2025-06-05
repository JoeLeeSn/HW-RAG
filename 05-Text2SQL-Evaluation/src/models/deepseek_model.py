import os
import json
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DeepSeekText2SQL:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DeepSeek模型
        
        Args:
            config: 配置字典，包含以下字段：
                - api_key: DeepSeek API密钥
                - model: 模型名称
                - temperature: 温度参数
        """
        self.api_key = config.get('api_key') or os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未设置")
            
        self.model = config.get('model', 'deepseek-chat')
        self.temperature = config.get('temperature', 0.1)
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
    def generate_sql(self, question: str, schema_info: str) -> str:
        """
        生成SQL查询
        
        Args:
            question: 自然语言问题
            schema_info: 数据库模式信息
            
        Returns:
            生成的SQL查询
        """
        try:
            # 构建提示
            prompt = f"""你是一个专业的SQL生成助手。请根据以下数据库模式信息和问题生成对应的SQL查询。

数据库模式信息：
{schema_info}

问题：{question}

请只返回SQL查询语句，不要包含任何其他解释。"""

            # 调用API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的SQL生成助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature
            }
            
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            sql = result['choices'][0]['message']['content'].strip()
            
            # 清理SQL（移除可能的markdown代码块标记）
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            return sql
            
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {str(e)}")
            raise 