import logging
import logging.config
import os
import sys
import json
import yaml
from dotenv import load_dotenv
from database import DatabaseManager
from evaluator import Text2SQLEvaluator
from report_generator import ReportGenerator
from config import LOG_CONFIG, EVAL_CONFIG

# 配置日志
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

def load_config() -> dict:
    """
    加载配置信息
    
    Returns:
        配置字典
    """
    # 加载环境变量
    load_dotenv('/home/gssnet/rag-in-action/.env')
    
    # 使用 config.py 中的配置
    return EVAL_CONFIG

def main():
    """主函数"""
    try:
        # 加载配置
        logger.info("开始加载配置...")
        config = load_config()
        logger.info("配置加载完成")
        
        # 初始化评估器
        logger.info("初始化评估器...")
        evaluator = Text2SQLEvaluator(config)
        logger.info("评估器初始化完成")
        
        # 执行评估
        logger.info("开始评估模型...")
        results = evaluator.evaluate_models()
        logger.info("模型评估完成")
        
        # 生成报告
        logger.info("生成评估报告...")
        report_generator = ReportGenerator()
        report_path = report_generator.generate_report(results)
        logger.info(f"评估完成！报告已生成在: {report_path}")
        
    except Exception as e:
        logger.error(f"评估过程中出错: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 