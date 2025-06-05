import logging
import json
import yaml
import random
import time
import re
from typing import List, Dict, Any, Tuple, Optional
from tqdm import tqdm
from database import DatabaseManager
from metrics import MetricsCalculator
from config import EVAL_CONFIG, DB_CONFIG
from models.deepseek_model import DeepSeekText2SQL
from models.openai_model import OpenAIText2SQL
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

logger = logging.getLogger(__name__)

class Text2SQLEvaluator:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化评估器
        
        Args:
            config: 配置字典，包含以下字段：
                - test_data_path: 测试数据路径
                - schema_path: 数据库模式信息路径
                - ddl_path: DDL语句路径
                - sample_size: 随机抽样数量
                - metrics: 评估指标列表
                - model_config: 模型配置
        """
        self.config = config
        self.db_manager = DatabaseManager()
        self.metrics = MetricsCalculator(self.db_manager)
        
        # 加载测试数据
        with open(self.config['test_data_path'], 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
            
        # 加载数据库模式信息
        with open(self.config['schema_path'], 'r', encoding='utf-8') as f:
            self.schema_info = yaml.safe_load(f)
            
        # 加载DDL语句
        with open(self.config['ddl_path'], 'r', encoding='utf-8') as f:
            self.ddl_statements = yaml.safe_load(f)
            
        # 初始化模型
        self.models = {}
        self._init_models()
        
    def _init_models(self):
        """初始化模型"""
        for model_name, model_config in self.config['model_config'].items():
            if model_name == 'qwen':
                # 初始化通义千问模型
                self.models[model_name] = {
                    'tokenizer': AutoTokenizer.from_pretrained(
                        model_config['model_path'],
                        trust_remote_code=True,
                        model_type=model_config.get('model_type', 'qwen3')
                    ),
                    'model': AutoModelForCausalLM.from_pretrained(
                        model_config['model_path'],
                        device_map='auto',
                        trust_remote_code=True,
                        model_type=model_config.get('model_type', 'qwen3')
                    ),
                    'config': model_config
                }
            elif model_name == 'deepseek':
                # 保持原有的DeepSeek配置
                self.models[model_name] = model_config
                
    def _prepare_schema_info(self) -> str:
        """
        准备数据库模式信息字符串
        
        Returns:
            格式化的数据库模式信息
        """
        schema_str = []
        for table_name, fields in self.schema_info.items():
            schema_str.append(f"{table_name}（{table_name}表）")
            schema_str.append("字段：")
            for field_name, description in fields.items():
                schema_str.append(f"  - {field_name}: {description}")
            schema_str.append("")
        return "\n".join(schema_str)
        
    def _generate_sql_with_qwen(self, question: str, model_name: str) -> str:
        """使用通义千问模型生成SQL"""
        model_info = self.models[model_name]
        tokenizer = model_info['tokenizer']
        model = model_info['model']
        config = model_info['config']
        
        # 构建提示词
        schema_info = self._prepare_schema_info()
        prompt = f"""以下是数据库的结构描述：
{schema_info}

用户的自然语言问题如下：
"{question}"

请只返回SQL语句，不要包含任何解释或说明。确保：
1. 使用正确的表名和字段名（注意大小写）
2. 确保SQL语句以分号结尾
3. 只使用上述表结构中的表和字段
4. 不要使用不存在的表或字段
5. 对于INSERT语句，不要包含last_update字段，除非明确要求
6. 对于SELECT语句，确保FROM子句使用正确的表名
7. 对于JOIN操作，确保使用正确的关联条件

SQL:"""
        
        # 生成回答
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=config['max_length'],
            do_sample=True,
            top_p=0.9,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.2,
            temperature=0.1
        )
        
        # 解码并提取SQL
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        sql = response.split("SQL:")[-1].strip()
        
        # 清理SQL语句
        sql = self._clean_sql(sql)
        return sql
        
    def _extract_sql(self, text: str) -> str:
        """提取SQL语句"""
        # 尝试匹配SQL代码块
        sql_blocks = re.findall(r'```sql\n(.*?)\n```', text, re.DOTALL)
        if sql_blocks:
            return sql_blocks[0].strip()
        
        # 如果没有找到代码块，尝试匹配SELECT语句
        select_match = re.search(r'SELECT.*?;', text, re.DOTALL)
        if select_match:
            return select_match.group(0).strip()
        
        # 如果都没有找到，返回原始文本
        return text.strip()
        
    def _clean_sql(self, sql: str) -> str:
        """
        清理和标准化SQL语句
        
        Args:
            sql: 原始SQL语句
            
        Returns:
            清理后的SQL语句
        """
        # 移除多余的空格和换行
        sql = ' '.join(sql.split())
        
        # 移除任何非SQL文本（如中文说明）
        sql = sql.split(';')[0] + ';'
        
        # 移除可能的Markdown标记
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        # 移除可能的"答案："等中文提示
        sql = sql.split('答案：')[-1].strip()
        
        # 标准化表名和字段名
        table_names = list(self.schema_info.keys())
        for table in table_names:
            # 替换各种大小写变体
            patterns = [
                (f" {table.upper()} ", f" {table} "),
                (f" {table.lower()} ", f" {table} "),
                (f" {table.title()} ", f" {table} "),
                (f" {table.upper()},", f" {table},"),
                (f" {table.lower()},", f" {table},"),
                (f" {table.title()},", f" {table},"),
                (f" {table.upper()};", f" {table};"),
                (f" {table.lower()};", f" {table};"),
                (f" {table.title()};", f" {table};"),
                (f" {table.upper()} AS ", f" {table} AS "),
                (f" {table.lower()} AS ", f" {table} AS "),
                (f" {table.title()} AS ", f" {table} AS "),
                # 添加更多模式以处理可能的变体
                (f" {table.upper()}.", f" {table}."),
                (f" {table.lower()}.", f" {table}."),
                (f" {table.title()}.", f" {table}."),
                (f" {table.upper()})", f" {table})"),
                (f" {table.lower()})", f" {table})"),
                (f" {table.title()})", f" {table})"),
                (f"({table.upper()} ", f"({table} "),
                (f"({table.lower()} ", f"({table} "),
                (f"({table.title()} ", f"({table} ")
            ]
            for pattern, replacement in patterns:
                sql = sql.replace(pattern, replacement)
            
        # 标准化关键字大小写
        keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 
                   'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'ON', 'AND', 
                   'OR', 'LIMIT', 'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM',
                   'EXISTS', 'NOT EXISTS', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'BETWEEN',
                   'IS NULL', 'IS NOT NULL', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
        for keyword in keywords:
            sql = sql.replace(keyword.lower(), keyword)
            sql = sql.replace(keyword.upper(), keyword)
            
        # 确保SQL语句以分号结尾
        if not sql.endswith(';'):
            sql += ';'
            
        return sql
        
    def _validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        验证SQL语句
        
        Args:
            sql: SQL语句
            
        Returns:
            Tuple[bool, Optional[str]]: 
            - 是否有效
            - 错误信息（如果有）
        """
        # 1. 检查表名是否存在
        table_names = list(self.schema_info.keys())
        sql_lower = sql.lower()
        used_tables = []
        
        # 提取SQL中使用的表名
        words = sql_lower.split()
        for i, word in enumerate(words):
            if word in ['from', 'join', 'into', 'update']:
                # 获取下一个词作为表名
                if i + 1 < len(words):
                    table = words[i + 1].strip(';').strip(',').strip(')').strip('(')
                    if table in [t.lower() for t in table_names]:
                        used_tables.append(table)
                    elif table not in ['as', 'on', 'where', 'group', 'order', 'having', 'limit']:
                        return False, f"SQL语句中使用了不存在的表: {table}"
                        
        if not used_tables:
            return False, f"SQL语句中未找到有效的表名。可用的表名: {', '.join(table_names)}"
            
        # 2. 检查基本语法
        if not sql.strip().endswith(';'):
            return False, "SQL语句必须以分号结尾"
            
        # 3. 检查关键字使用
        if 'select' in sql_lower and 'from' not in sql_lower:
            return False, "SELECT语句必须包含FROM子句"
            
        # 4. 使用数据库验证
        return self.db_manager.validate_sql(sql)
        
    def evaluate_models(self) -> Dict[str, Dict[str, Any]]:
        """
        评估所有模型
        
        Returns:
            评估结果字典
        """
        results = {}
        
        # 加载测试数据
        with open(self.config['test_data_path'], 'r', encoding='utf-8') as f:
            test_data = json.load(f)
            
        # 限制样本数量
        test_data = test_data[:self.config['sample_size']]
        
        # 评估每个模型
        for model_name in tqdm(self.models.keys(), desc="评估进度"):
            model_results = {
                'exact_match_rate': 0,
                'execution_match_rate': 0,
                'syntax_check_rate': 0,
                'complexity_scores': [],
                'result_set_metrics': {
                    'precision': [],
                    'recall': [],
                    'f1_score': [],
                    'size_ratio': []
                },
                'execution_metrics': {
                    'efficiency_scores': [],
                    'avg_time': 0,
                    'avg_result_size': 0
                },
                'errors': {
                    'syntax': 0,
                    'execution': 0,
                    'result_mismatch': 0
                }
            }
            
            total_samples = len(test_data)
            exact_matches = 0
            execution_matches = 0
            syntax_correct = 0
            
            for sample in test_data:
                try:
                    logger.info(f"\n{'='*50}\n评估样本 {sample['id'] if 'id' in sample else '未知'}")
                    logger.info(f"问题: {sample['question']}")
                    logger.info(f"参考SQL: {sample['sql']}")
                    
                    # 生成SQL
                    if model_name == 'qwen':
                        generated_sql = self._generate_sql_with_qwen(sample['question'], model_name)
                    elif model_name == 'deepseek':
                        # 使用 DeepSeek 模型生成 SQL
                        model = DeepSeekText2SQL(self.models[model_name])
                        generated_sql = model.generate_sql(sample['question'], self._prepare_schema_info())
                        generated_sql = self._clean_sql(generated_sql)
                    else:
                        continue
                        
                    logger.info(f"生成的SQL ({model_name}): {generated_sql}")
                    
                    # 评估生成的SQL
                    # 1. 检查语法
                    syntax_ok, syntax_error = self._validate_sql(generated_sql)
                    if syntax_ok:
                        syntax_correct += 1
                        logger.info(f"SQL语法检查通过")
                    else:
                        model_results['errors']['syntax'] += 1
                        logger.warning(f"SQL语法错误 ({model_name}): {syntax_error}")
                        continue
                        
                    # 2. 检查精确匹配
                    if generated_sql.strip().upper() == sample['sql'].strip().upper():
                        exact_matches += 1
                        logger.info("SQL精确匹配")
                    else:
                        logger.info("SQL不完全匹配")
                        
                    # 3. 执行SQL并比较结果
                    success, exec_result, exec_error = self.db_manager.execute_query(generated_sql)
                    if success:
                        # 执行参考SQL
                        ref_success, ref_result, _ = self.db_manager.execute_query(sample['sql'])
                        if ref_success and self.db_manager.compare_results(exec_result, ref_result):
                            execution_matches += 1
                            logger.info("执行结果匹配")
                        else:
                            model_results['errors']['result_mismatch'] += 1
                            logger.warning(f"结果不匹配:\n生成的SQL结果: {exec_result}\n参考SQL结果: {ref_result}")
                    else:
                        model_results['errors']['execution'] += 1
                        logger.warning(f"SQL执行错误: {exec_error}")
                        
                    # 4. 计算复杂度评分
                    complexity_score = self.metrics.calculate_query_complexity_score(generated_sql)
                    model_results['complexity_scores'].append(complexity_score)
                    logger.info(f"查询复杂度评分: {complexity_score}")
                    
                    # 5. 计算执行时间
                    execution_time, _ = self.metrics.calculate_execution_time(generated_sql)
                    model_results['execution_metrics']['avg_time'] += execution_time
                    logger.info(f"执行时间: {execution_time}ms")
                    
                    # 6. 计算结果集大小
                    if success and exec_result:
                        result_size = len(exec_result)
                        model_results['execution_metrics']['avg_result_size'] += result_size
                        logger.info(f"结果集大小: {result_size}")
                        
                except Exception as e:
                    logger.error(f"模型 {model_name} 处理样本时出错: {str(e)}")
                    continue
                    
            # 计算最终指标
            if total_samples > 0:
                model_results['exact_match_rate'] = (exact_matches / total_samples) * 100
                model_results['execution_match_rate'] = (execution_matches / total_samples) * 100
                model_results['syntax_check_rate'] = (syntax_correct / total_samples) * 100
                
                if model_results['execution_metrics']['avg_time'] > 0:
                    model_results['execution_metrics']['avg_time'] /= total_samples
                if model_results['execution_metrics']['avg_result_size'] > 0:
                    model_results['execution_metrics']['avg_result_size'] /= total_samples
                    
            results[model_name] = model_results
            
        return results

    def evaluate(self, generated_sqls: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        评估生成的SQL
        
        Args:
            generated_sqls: 生成的SQL列表
            
        Returns:
            Tuple[List[Dict], Dict]: 
            - 详细评估结果
            - 评估总结
        """
        results = []
        metrics = {
            'exact_match': 0,
            'execution_success': 0,
            'result_match': 0,
            'syntax_correct': 0,
            'has_join': 0,
            'has_subquery': 0,
            'has_group_by': 0,
            'has_having': 0,
            'has_order_by': 0,
            'has_limit': 0,
            'syntax_errors': 0,
            'execution_errors': 0,
            'result_mismatches': 0,
            'total_time': 0
        }
        
        test_cases = self.load_test_data()
        
        for i, (case, gen_sql) in enumerate(tqdm(zip(test_cases, generated_sqls))):
            result = {
                'question': case['question'],
                'reference_sql': case['sql'],
                'generated_sql': gen_sql,
                'exact_match': False,
                'execution_success': False,
                'result_match': False,
                'syntax_correct': False,
                'error': None,
                'execution_time': 0
            }
            
            # 检查语法
            syntax_ok, syntax_error = self.db_manager.validate_sql(gen_sql)
            result['syntax_correct'] = syntax_ok
            if syntax_ok:
                metrics['syntax_correct'] += 1
            else:
                metrics['syntax_errors'] += 1
                result['error'] = f"语法错误: {syntax_error}"
                results.append(result)
                continue
            
            # 检查精确匹配
            if gen_sql.strip().upper() == case['sql'].strip().upper():
                result['exact_match'] = True
                metrics['exact_match'] += 1
            
            # 执行SQL
            success, exec_result, exec_error = self.db_manager.execute_query(gen_sql)
            result['execution_success'] = success
            
            if success:
                metrics['execution_success'] += 1
                
                # 如果是SELECT查询，比较结果
                if gen_sql.strip().upper().startswith('SELECT'):
                    ref_success, ref_result, _ = self.db_manager.execute_query(case['sql'])
                    if ref_success and self.db_manager.compare_results(exec_result, ref_result):
                        result['result_match'] = True
                        metrics['result_match'] += 1
                    else:
                        metrics['result_mismatches'] += 1
                        result['error'] = "结果不匹配"
                else:
                    # 对于非SELECT操作，检查影响的行数
                    if exec_result and exec_result[0].get('affected_rows', 0) > 0:
                        result['result_match'] = True
                        metrics['result_match'] += 1
            else:
                metrics['execution_errors'] += 1
                result['error'] = f"执行错误: {exec_error}"
            
            # 分析查询复杂度
            sql_upper = gen_sql.upper()
            if 'JOIN' in sql_upper:
                metrics['has_join'] += 1
            if 'SELECT' in sql_upper and '(' in sql_upper and ')' in sql_upper:
                metrics['has_subquery'] += 1
            if 'GROUP BY' in sql_upper:
                metrics['has_group_by'] += 1
            if 'HAVING' in sql_upper:
                metrics['has_having'] += 1
            if 'ORDER BY' in sql_upper:
                metrics['has_order_by'] += 1
            if 'LIMIT' in sql_upper:
                metrics['has_limit'] += 1
            
            results.append(result)
        
        # 计算总结
        total = len(test_cases)
        summary = {
            'total_cases': total,
            'exact_match_rate': metrics['exact_match'] / total * 100,
            'execution_success_rate': metrics['execution_success'] / total * 100,
            'result_match_rate': metrics['result_match'] / total * 100,
            'syntax_correct_rate': metrics['syntax_correct'] / total * 100,
            'avg_execution_time': metrics['total_time'] / total if total > 0 else 0,
            'query_complexity': {
                'has_join': metrics['has_join'] / total * 100,
                'has_subquery': metrics['has_subquery'] / total * 100,
                'has_group_by': metrics['has_group_by'] / total * 100,
                'has_having': metrics['has_having'] / total * 100,
                'has_order_by': metrics['has_order_by'] / total * 100,
                'has_limit': metrics['has_limit'] / total * 100
            },
            'error_distribution': {
                'syntax_errors': metrics['syntax_errors'] / total * 100,
                'execution_errors': metrics['execution_errors'] / total * 100,
                'result_mismatches': metrics['result_mismatches'] / total * 100
            }
        }
        
        return results, summary 