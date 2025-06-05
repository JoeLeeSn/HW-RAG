# Text2SQL 模型评估与比较系统

## 1. 系统概述

本系统用于评估和比较不同大语言模型（DeepSeek和通义千问）在Text2SQL任务上的性能。系统基于Sakila数据库，通过多个维度对模型生成的SQL语句进行全面评估和对比分析。

## 2. 评估维度

### 2.1 准确性评估
- 精确匹配率：生成的SQL与参考SQL的完全匹配程度
- 执行成功率：生成的SQL能否成功执行
- 结果匹配率：生成的SQL执行结果与参考SQL执行结果的一致性
- 语法正确率：SQL语法验证结果

### 2.2 性能评估
- 执行时间：SQL查询的执行耗时
- 查询复杂度分析：
  - JOIN操作使用情况
  - 子查询使用情况
  - GROUP BY使用情况
  - HAVING使用情况
  - ORDER BY使用情况
  - LIMIT使用情况

### 2.3 错误分析
- 语法错误：SQL语法验证失败
- 执行错误：运行时错误（如完整性约束违反）
- 结果不匹配：执行结果与预期不符

## 3. 系统组件

### 3.1 数据库管理 (DatabaseManager)
- 数据库连接管理
- SQL执行和验证
- 结果比较
- 表结构查询
- SQL语法验证

### 3.2 模型实现
- 通义千问模型实现
  - 基于通义千问大语言模型
  - 支持数据库模式信息注入
- DeepSeek模型实现
  - 基于DeepSeek大语言模型
  - 支持数据库模式信息注入

### 3.3 评估器 (Text2SQLEvaluator)
- 测试数据加载和随机抽样
- 批量评估执行
- 指标计算和汇总
- 错误捕获和分析
- 模型性能对比

## 4. 评估流程

1. 加载测试数据（从q2sql_pairs.json随机抽样）
2. 加载数据库模式信息（db_description.yaml和ddl_statements.yaml）
3. 执行SQL生成：
   - 通义千问模型生成
   - DeepSeek模型生成
4. 执行评估：
   - 语法验证
   - 精确匹配检查
   - SQL执行
   - 结果比较
5. 生成评估报告

## 5. 使用方法

### 5.1 环境配置
```bash
# 安装依赖
pip install -r requirements.txt

# 使用指定的环境变量文件
cp /home/gssnet/rag-in-action/.env .env
# 确保.env文件包含以下配置：
# - 数据库连接信息
# - 模型配置
```

### 5.2 运行评估
```bash
cd src
python main.py
```

### 5.3 查看报告
评估报告将生成在`reports`目录下，包括：
- 文本报告（Markdown格式）

## 6. 配置说明

### 6.1 数据库配置
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'your_password',
    'database': 'sakila'
}
```

### 6.2 模型配置
```python
MODEL_CONFIG = {
    'qwen': {
        'model_path': 'Qwen/Qwen-7B-Chat',
        'model_type': 'qwen3',
        'max_length': 2048
    },
    'deepseek': {
        'model_path': 'deepseek-ai/deepseek-coder-6.7b-base',
        'device': 'cuda'
    }
}
```

### 6.3 评估配置
```python
EVAL_CONFIG = {
    'test_data_path': '90-文档-Data/sakila/q2sql_pairs.json',
    'schema_path': '90-文档-Data/sakila/db_description.yaml',
    'ddl_path': '90-文档-Data/sakila/ddl_statements.yaml',
    'sample_size': 50,  # 随机抽样数量
    'metrics': ['exact_match', 'execution_match', 'syntax_check']
}
```

## 7. 依赖说明

主要依赖包：
- pymysql>=1.1.0
- sqlalchemy>=2.0.0
- tqdm>=4.65.0
- python-dotenv>=1.0.0
- transformers>=4.30.0
- pyyaml>=6.0.0
- torch>=2.0.0 