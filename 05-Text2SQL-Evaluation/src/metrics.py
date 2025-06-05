import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from database import DatabaseManager
import re

logger = logging.getLogger(__name__)

class MetricsCalculator:
    def __init__(self, db_manager: DatabaseManager):
        """初始化指标计算器"""
        self.db_manager = db_manager
        
    def calculate_exact_match(self, generated_sql: str, reference_sql: str) -> bool:
        """
        计算精确匹配率
        
        Args:
            generated_sql: 生成的SQL
            reference_sql: 参考SQL
            
        Returns:
            bool: 是否完全匹配
        """
        # 标准化SQL字符串（移除多余空格、统一大小写等）
        def normalize_sql(sql: str) -> str:
            return ' '.join(sql.lower().split())
            
        return normalize_sql(generated_sql) == normalize_sql(reference_sql)
        
    def calculate_execution_success(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        计算执行成功率
        
        Args:
            sql: SQL语句
            
        Returns:
            Tuple[bool, Optional[str]]: 
            - 是否执行成功
            - 错误信息（如果有）
        """
        success, _, error = self.db_manager.execute_query(sql)
        return success, error
        
    def calculate_result_match(self, generated_sql: str, reference_sql: str) -> Tuple[bool, Optional[str]]:
        """
        计算结果匹配率
        
        Args:
            generated_sql: 生成的SQL
            reference_sql: 参考SQL
            
        Returns:
            Tuple[bool, Optional[str]]: 
            - 结果是否匹配
            - 错误信息（如果有）
        """
        # 执行生成的SQL
        success1, result1, error1 = self.db_manager.execute_query(generated_sql)
        if not success1:
            return False, error1
            
        # 执行参考SQL
        success2, result2, error2 = self.db_manager.execute_query(reference_sql)
        if not success2:
            return False, error2
            
        # 比较结果
        return self.db_manager.compare_results(result1, result2), None
        
    def calculate_syntax_correctness(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        计算语法正确率
        
        Args:
            sql: SQL语句
            
        Returns:
            Tuple[bool, Optional[str]]: 
            - 语法是否正确
            - 错误信息（如果有）
        """
        return self.db_manager.validate_sql(sql)
        
    def calculate_query_complexity(self, sql: str) -> Dict[str, Any]:
        """
        计算查询复杂度
        
        Args:
            sql: SQL语句
            
        Returns:
            Dict[str, Any]: 复杂度指标
        """
        complexity = {
            'has_join': False,
            'has_subquery': False,
            'has_group_by': False,
            'has_having': False,
            'has_order_by': False,
            'has_limit': False,
            'join_count': 0,
            'subquery_count': 0,
            'condition_count': 0
        }
        
        sql_lower = sql.lower()
        
        # 检查各种SQL特性
        complexity['has_join'] = 'join' in sql_lower
        complexity['has_subquery'] = '(' in sql_lower and 'select' in sql_lower[sql_lower.find('('):]
        complexity['has_group_by'] = 'group by' in sql_lower
        complexity['has_having'] = 'having' in sql_lower
        complexity['has_order_by'] = 'order by' in sql_lower
        complexity['has_limit'] = 'limit' in sql_lower
        
        # 计算JOIN数量
        complexity['join_count'] = sql_lower.count('join')
        
        # 计算子查询数量
        complexity['subquery_count'] = sql_lower.count('(select')
        
        # 计算条件数量
        complexity['condition_count'] = sql_lower.count('where') + sql_lower.count('and') + sql_lower.count('or')
        
        return complexity
        
    def calculate_execution_time(self, sql: str) -> Tuple[float, Optional[str]]:
        """
        计算执行时间
        
        Args:
            sql: SQL语句
            
        Returns:
            Tuple[float, Optional[str]]: 
            - 执行时间（秒）
            - 错误信息（如果有）
        """
        try:
            start_time = time.time()
            success, _, error = self.db_manager.execute_query(sql)
            end_time = time.time()
            
            if not success:
                return 0.0, error
                
            return end_time - start_time, None
        except Exception as e:
            return 0.0, str(e)
            
    def calculate_query_complexity_score(self, sql: str) -> float:
        """
        计算查询复杂度评分
        
        Args:
            sql: SQL查询语句
            
        Returns:
            复杂度评分 (0-1)
        """
        # 基础分数
        score = 0.0
        
        # 检查JOIN
        if re.search(r'\bJOIN\b', sql, re.IGNORECASE):
            score += 0.2
            
        # 检查子查询
        if re.search(r'\(.*SELECT.*\)', sql, re.IGNORECASE):
            score += 0.2
            
        # 检查GROUP BY
        if re.search(r'\bGROUP BY\b', sql, re.IGNORECASE):
            score += 0.15
            
        # 检查HAVING
        if re.search(r'\bHAVING\b', sql, re.IGNORECASE):
            score += 0.15
            
        # 检查ORDER BY
        if re.search(r'\bORDER BY\b', sql, re.IGNORECASE):
            score += 0.1
            
        # 检查LIMIT
        if re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
            score += 0.1
            
        # 检查聚合函数
        if re.search(r'\b(COUNT|SUM|AVG|MAX|MIN)\b', sql, re.IGNORECASE):
            score += 0.1
            
        return min(score, 1.0)
        
    def compare_result_sets(self, ref_result: List[Tuple], gen_result: List[Tuple]) -> Dict[str, float]:
        """
        比较结果集
        
        Args:
            ref_result: 参考结果集
            gen_result: 生成结果集
            
        Returns:
            比较结果字典
        """
        # 计算结果集大小
        ref_size = len(ref_result)
        gen_size = len(gen_result)
        
        # 计算交集大小
        intersection = set(ref_result) & set(gen_result)
        intersection_size = len(intersection)
        
        # 计算相似度指标
        precision = intersection_size / gen_size if gen_size > 0 else 0
        recall = intersection_size / ref_size if ref_size > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'size_ratio': gen_size / ref_size if ref_size > 0 else 0
        }
        
    def analyze_query_structure(self, sql: str) -> Dict[str, Any]:
        """
        分析查询结构
        
        Args:
            sql: SQL查询语句
            
        Returns:
            查询结构分析结果
        """
        analysis = {
            'has_join': bool(re.search(r'\bJOIN\b', sql, re.IGNORECASE)),
            'has_subquery': bool(re.search(r'\(.*SELECT.*\)', sql, re.IGNORECASE)),
            'has_group_by': bool(re.search(r'\bGROUP BY\b', sql, re.IGNORECASE)),
            'has_having': bool(re.search(r'\bHAVING\b', sql, re.IGNORECASE)),
            'has_order_by': bool(re.search(r'\bORDER BY\b', sql, re.IGNORECASE)),
            'has_limit': bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE)),
            'has_aggregation': bool(re.search(r'\b(COUNT|SUM|AVG|MAX|MIN)\b', sql, re.IGNORECASE)),
            'table_count': len(re.findall(r'\bFROM\b.*?\b(?:WHERE|GROUP|ORDER|LIMIT|$)', sql, re.IGNORECASE)),
            'condition_count': len(re.findall(r'\bWHERE\b.*?(?:\b(?:GROUP|ORDER|LIMIT)\b|$)', sql, re.IGNORECASE))
        }
        
        return analysis
        
    def calculate_execution_metrics(self, execution_time: float, result_size: int) -> Dict[str, float]:
        """
        计算执行指标
        
        Args:
            execution_time: 执行时间（毫秒）
            result_size: 结果集大小
            
        Returns:
            执行指标字典
        """
        return {
            'execution_time': execution_time,
            'result_size': result_size,
            'efficiency_score': 1.0 / (execution_time * result_size) if execution_time > 0 and result_size > 0 else 0
        }
        
    def calculate_all_metrics(self, generated_sql: str, reference_sql: str) -> Dict[str, Any]:
        """
        计算所有评估指标
        
        Args:
            generated_sql: 生成的SQL
            reference_sql: 参考SQL
            
        Returns:
            Dict[str, Any]: 所有评估指标
        """
        metrics = {}
        
        # 计算精确匹配率
        metrics['exact_match'] = self.calculate_exact_match(generated_sql, reference_sql)
        
        # 计算执行成功率
        metrics['execution_success'], metrics['execution_error'] = self.calculate_execution_success(generated_sql)
        
        # 计算结果匹配率
        metrics['result_match'], metrics['result_error'] = self.calculate_result_match(generated_sql, reference_sql)
        
        # 计算语法正确率
        metrics['syntax_correct'], metrics['syntax_error'] = self.calculate_syntax_correctness(generated_sql)
        
        # 计算查询复杂度
        metrics['complexity'] = self.calculate_query_complexity(generated_sql)
        
        # 计算执行时间
        metrics['execution_time'], metrics['time_error'] = self.calculate_execution_time(generated_sql)
        
        return metrics 