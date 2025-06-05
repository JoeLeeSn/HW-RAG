import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List, Tuple, Dict, Any, Optional
from config import DB_CONFIG
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """初始化数据库管理器"""
        self.engine = self._create_engine()
        
    def _create_engine(self):
        """创建数据库引擎"""
        try:
            # URL编码密码，处理特殊字符
            password = quote_plus(DB_CONFIG['password'])
            
            # 构建连接字符串
            if 'unix_socket' in DB_CONFIG:
                connection_string = (
                    f"mysql+pymysql://{DB_CONFIG['user']}:{password}"
                    f"@localhost/{DB_CONFIG['database']}"
                    f"?unix_socket={DB_CONFIG['unix_socket']}"
                )
            else:
                connection_string = (
                    f"mysql+pymysql://{DB_CONFIG['user']}:{password}"
                    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
                )
            
            logger.debug(f"数据库连接字符串: {connection_string}")
            return create_engine(connection_string)
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def execute_query(self, sql: str) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            
        Returns:
            Tuple[bool, Optional[List[Dict]], Optional[str]]: 
            - 执行是否成功
            - 查询结果（如果成功）
            - 错误信息（如果失败）
        """
        try:
            with self.engine.connect() as conn:
                # 开始事务
                with conn.begin():
                    # 检查SQL类型
                    sql_type = self._get_sql_type(sql)
                    
                    # 执行SQL
                    result = conn.execute(text(sql))
                    
                    # 根据SQL类型处理结果
                    if sql_type == 'SELECT':
                        columns = result.keys()
                        rows = result.fetchall()
                        results = [dict(zip(columns, row)) for row in rows]
                        return True, results, None
                    else:
                        # 对于非SELECT操作，返回影响的行数
                        return True, [{'affected_rows': result.rowcount}], None
                
        except IntegrityError as e:
            error_msg = str(e)
            logger.error(f"完整性约束错误: {error_msg}")
            return False, None, f"完整性约束错误: {error_msg}"
        except SQLAlchemyError as e:
            error_msg = str(e)
            logger.error(f"SQL执行错误: {error_msg}")
            return False, None, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.error(f"未知错误: {error_msg}")
            return False, None, error_msg

    def _get_sql_type(self, sql: str) -> str:
        """
        获取SQL语句类型
        
        Args:
            sql: SQL语句
            
        Returns:
            str: SQL类型 (SELECT, INSERT, UPDATE, DELETE)
        """
        sql = sql.strip().upper()
        if sql.startswith('SELECT'):
            return 'SELECT'
        elif sql.startswith('INSERT'):
            return 'INSERT'
        elif sql.startswith('UPDATE'):
            return 'UPDATE'
        elif sql.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'UNKNOWN'

    def check_foreign_key_constraints(self, table: str, id_value: int) -> Tuple[bool, Optional[str]]:
        """
        检查外键约束
        
        Args:
            table: 表名
            id_value: ID值
            
        Returns:
            Tuple[bool, Optional[str]]: 
            - 是否可以安全操作
            - 错误信息（如果有）
        """
        try:
            with self.engine.connect() as conn:
                # 查询外键约束
                query = f"""
                SELECT 
                    TABLE_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE
                    REFERENCED_TABLE_SCHEMA = '{DB_CONFIG['database']}'
                    AND REFERENCED_TABLE_NAME = '{table}'
                """
                result = conn.execute(text(query))
                constraints = [dict(row) for row in result]
                
                if not constraints:
                    return True, None
                
                # 检查每个约束
                for constraint in constraints:
                    check_query = f"""
                    SELECT COUNT(*) as count
                    FROM {constraint['TABLE_NAME']}
                    WHERE {constraint['COLUMN_NAME']} = {id_value}
                    """
                    result = conn.execute(text(check_query))
                    count = result.scalar()
                    
                    if count > 0:
                        return False, f"记录被 {constraint['TABLE_NAME']} 表引用，无法删除"
                
                return True, None
                
        except Exception as e:
            logger.error(f"检查外键约束失败: {str(e)}")
            return False, str(e)

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        验证SQL语法
        
        Args:
            sql: SQL查询语句
            
        Returns:
            Tuple[bool, Optional[str]]: 
            - 语法是否正确
            - 错误信息（如果有）
        """
        try:
            with self.engine.connect() as conn:
                # 使用EXPLAIN验证SQL语法
                conn.execute(text(f"EXPLAIN {sql}"))
                return True, None
        except SQLAlchemyError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def compare_results(self, result1: List[Dict[str, Any]], result2: List[Dict[str, Any]]) -> bool:
        """
        比较两个查询结果是否相同
        
        Args:
            result1: 第一个查询结果
            result2: 第二个查询结果
            
        Returns:
            bool: 结果是否相同
        """
        if len(result1) != len(result2):
            return False
            
        # 将结果转换为可比较的格式
        def normalize_result(result):
            return sorted([tuple(sorted(row.items())) for row in result])
            
        return normalize_result(result1) == normalize_result(result2)

    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            Optional[Dict[str, Any]]: 表结构信息
        """
        try:
            with self.engine.connect() as conn:
                # 获取列信息
                columns_query = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{DB_CONFIG['database']}'
                AND TABLE_NAME = '{table_name}'
                """
                result = conn.execute(text(columns_query))
                columns = [dict(row) for row in result]
                
                # 获取索引信息
                indexes_query = f"""
                SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = '{DB_CONFIG['database']}'
                AND TABLE_NAME = '{table_name}'
                """
                result = conn.execute(text(indexes_query))
                indexes = [dict(row) for row in result]
                
                return {
                    'table_name': table_name,
                    'columns': columns,
                    'indexes': indexes
                }
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return None 