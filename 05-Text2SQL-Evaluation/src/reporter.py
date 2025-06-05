import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import seaborn as sns
from config import REPORT_CONFIG

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        """初始化报告生成器"""
        self.output_dir = REPORT_CONFIG['output_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_report(self, results: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
        """
        生成评估报告
        
        Args:
            results: 详细评估结果
            summary: 评估总结
            
        Returns:
            str: 报告文件路径
        """
        try:
            # 生成文本报告
            report_content = self.generate_text_report(results, summary)
            
            # 生成可视化
            self.generate_visualizations(summary)
            
            # 保存报告
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = os.path.join(self.output_dir, f'evaluation_report_{timestamp}.md')
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            logger.info(f"评估报告已生成: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            raise
            
    def generate_text_report(self, results: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
        """生成文本格式的评估报告"""
        report = []
        
        # 标题
        report.append("# Text2SQL 评估报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 总体指标
        report.append("## 总体评估指标")
        report.append(f"- 测试用例总数: {summary['total_cases']}")
        report.append(f"- 精确匹配率: {summary['exact_match_rate']:.2f}%")
        report.append(f"- 执行成功率: {summary['execution_success_rate']:.2f}%")
        report.append(f"- 结果匹配率: {summary['result_match_rate']:.2f}%")
        report.append(f"- 语法正确率: {summary['syntax_correct_rate']:.2f}%")
        report.append(f"- 平均执行时间: {summary['avg_execution_time']:.2f}ms\n")
        
        # 查询复杂度分布
        report.append("## 查询复杂度分析")
        for key, value in summary['query_complexity'].items():
            report.append(f"- {key}: {value:.2f}%")
        report.append("")
        
        # 错误分布
        report.append("## 错误分析")
        for key, value in summary['error_distribution'].items():
            report.append(f"- {key}: {value:.2f}%")
        report.append("")
        
        # 详细结果
        report.append("## 详细评估结果")
        for i, result in enumerate(results, 1):
            report.append(f"\n### 测试用例 {i}")
            report.append(f"问题: {result['question']}")
            report.append(f"参考SQL: {result['reference_sql']}")
            report.append(f"生成SQL: {result['generated_sql']}")
            report.append(f"评估结果:")
            report.append(f"- 精确匹配: {'是' if result['exact_match'] else '否'}")
            report.append(f"- 执行成功: {'是' if result['execution_success'] else '否'}")
            report.append(f"- 结果匹配: {'是' if result['result_match'] else '否'}")
            report.append(f"- 语法正确: {'是' if result['syntax_correct'] else '否'}")
            if result['error']:
                report.append(f"- 错误信息: {result['error']}")
            report.append(f"- 执行时间: {result['execution_time']}ms")
            
        return "\n".join(report)
        
    def generate_visualizations(self, summary: Dict[str, Any]):
        """生成可视化图表"""
        # 设置图表样式
        sns.set_style("whitegrid")
        
        # 创建图表目录
        plots_dir = os.path.join(self.output_dir, 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        
        # 1. 主要指标对比图
        plt.figure(figsize=(10, 6))
        metrics = ['exact_match_rate', 'execution_success_rate', 
                  'result_match_rate', 'syntax_correct_rate']
        values = [summary[m] for m in metrics]
        plt.bar(metrics, values)
        plt.title('主要评估指标')
        plt.xticks(rotation=45)
        plt.ylabel('百分比 (%)')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'main_metrics.png'))
        plt.close()
        
        # 2. 查询复杂度分布图
        plt.figure(figsize=(10, 6))
        complexity = summary['query_complexity']
        plt.bar(complexity.keys(), complexity.values())
        plt.title('查询复杂度分布')
        plt.xticks(rotation=45)
        plt.ylabel('百分比 (%)')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'query_complexity.png'))
        plt.close()
        
        # 3. 错误分布图
        plt.figure(figsize=(10, 6))
        errors = summary['error_distribution']
        plt.bar(errors.keys(), errors.values())
        plt.title('错误分布')
        plt.xticks(rotation=45)
        plt.ylabel('百分比 (%)')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'error_distribution.png'))
        plt.close() 