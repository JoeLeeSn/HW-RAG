"""
Text2SQL模型实现
"""

from .deepseek_model import DeepSeekText2SQL
from .openai_model import OpenAIText2SQL

__all__ = ['DeepSeekText2SQL', 'OpenAIText2SQL'] 