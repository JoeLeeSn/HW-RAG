import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Root@123456',
    'database': 'sakila',
    'unix_socket': '/var/run/mysqld/mysqld.sock'
}

# 通义千问配置
QWEN_CONFIG = {
    'model_path': 'Qwen/Qwen1.5-0.5B',
    'model_type': 'qwen',
    'temperature': 0.1,
    'max_length': 2048
}

# DeepSeek配置
DEEPSEEK_CONFIG = {
    'api_key': os.getenv('DEEPSEEK_API_KEY'),
    'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
    'temperature': float(os.getenv('DEEPSEEK_TEMPERATURE', '0.1'))
}

# Milvus配置
MILVUS_CONFIG = {
    'db_path': 'text2sql_milvus_sakila.db'
}

# 评估配置
EVAL_CONFIG = {
    'test_data_path': os.path.join(WORKSPACE_ROOT, '90-文档-Data/sakila/q2sql_pairs.json'),
    'schema_path': os.path.join(WORKSPACE_ROOT, '90-文档-Data/sakila/db_description.yaml'),
    'ddl_path': os.path.join(WORKSPACE_ROOT, '90-文档-Data/sakila/ddl_statements.yaml'),
    'sample_size': 2,
    'metrics': [
        'exact_match',
        'execution_match',
        'syntax_check',
        'semantic_check'
    ],
    'model_config': {
        'deepseek': DEEPSEEK_CONFIG,
        'qwen': QWEN_CONFIG
    }
}

# 日志配置
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': os.path.join(PROJECT_ROOT, 'evaluation.log'),
            'mode': 'a'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

# 评估指标配置
METRICS_CONFIG = {
    'exact_match': True,
    'execution_success': True,
    'result_match': True,
    'syntax_correctness': True,
    'query_complexity': True,
    'execution_time': True
}

# 报告配置
REPORT_CONFIG = {
    'output_dir': os.path.join(PROJECT_ROOT, 'reports'),
    'template_dir': os.path.join(PROJECT_ROOT, 'templates'),
    'visualization_dir': os.path.join(PROJECT_ROOT, 'visualizations'),
    'include_visualizations': True,
    'include_error_analysis': True,
    'include_improvements': True
} 