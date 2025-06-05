import pymysql
from typing import Dict, Any, List, Tuple
import yaml
import logging
import time
import re

class DatabaseManager:
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置字典，包含以下字段：
                - host: 数据库主机
                - port: 数据库端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - unix_socket: Unix套接字路径（可选）
        """
        self.config = config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'Root@123456',
            'database': 'sakila',
            'unix_socket': '/var/run/mysqld/mysqld.sock'
        }
        self.connection = None
        self.last_execution_time = 0
        self.connect()
        
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                unix_socket=self.config.get('unix_socket')
            )
            logging.info("数据库连接成功")
        except Exception as e:
            logging.error(f"数据库连接失败: {str(e)}")
            raise
            
    def validate_sql_syntax(self, sql: str) -> bool:
        """
        验证SQL语法是否正确
        
        Args:
            sql: SQL查询语句
            
        Returns:
            语法是否正确
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"EXPLAIN {sql}")
            return True
        except Exception as e:
            logging.error(f"SQL语法错误: {str(e)}")
            return False
            
    def execute_sql(self, sql: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            
        Returns:
            (是否成功, 查询结果)
        """
        try:
            start_time = time.time()
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql)
                results = cursor.fetchall()
            self.last_execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
            return True, results
        except Exception as e:
            logging.error(f"SQL执行错误: {str(e)}")
            return False, []
            
    def get_last_execution_time(self) -> float:
        """
        获取最后一次SQL执行的耗时
        
        Returns:
            执行时间（毫秒）
        """
        return self.last_execution_time
        
    def analyze_query_complexity(self, sql: str) -> Dict[str, bool]:
        """
        分析SQL查询的复杂度
        
        Args:
            sql: SQL查询语句
            
        Returns:
            复杂度特征字典
        """
        sql = sql.lower()
        return {
            'joins': bool(re.search(r'\b(join|inner join|left join|right join|full join)\b', sql)),
            'subqueries': bool(re.search(r'\bselect\b.*\bselect\b', sql)),
            'group_by': bool(re.search(r'\bgroup by\b', sql)),
            'having': bool(re.search(r'\bhaving\b', sql)),
            'order_by': bool(re.search(r'\border by\b', sql)),
            'limit': bool(re.search(r'\blimit\b', sql))
        }
            
    def compare_results(self, results1: List[Dict[str, Any]], results2: List[Dict[str, Any]]) -> bool:
        """
        比较两个查询结果是否相同
        
        Args:
            results1: 第一个查询结果
            results2: 第二个查询结果
            
        Returns:
            结果是否相同
        """
        if len(results1) != len(results2):
            return False
            
        # 将结果转换为可比较的格式
        def normalize_result(result):
            if isinstance(result, dict):
                return tuple(sorted(result.items()))
            return result
            
        results1_normalized = [normalize_result(r) for r in results1]
        results2_normalized = [normalize_result(r) for r in results2]
        
        return sorted(results1_normalized) == sorted(results2_normalized)
        
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logging.info("数据库连接已关闭") 