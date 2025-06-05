import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

class ReportGenerator:
    def __init__(self):
        """初始化报告生成器"""
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_report(self, results: Dict[str, Dict[str, Any]]):
        """
        生成评估报告
        
        Args:
            results: 评估结果字典
        """
        # 生成文本报告
        report_content = []
        report_content.append("# Text2SQL 模型评估报告")
        report_content.append(f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 1. 总体性能对比
        report_content.append("## 1. 总体性能对比\n")
        report_content.append("### 1.1 准确率指标\n")
        report_content.append("| 模型 | 精确匹配率 | 执行匹配率 | 语法检查率 |")
        report_content.append("|------|------------|------------|------------|")
        
        for model_name, model_results in results.items():
            report_content.append(
                f"| {model_name} | "
                f"{model_results['exact_match_rate']:.2f}% | "
                f"{model_results['execution_match_rate']:.2f}% | "
                f"{model_results['syntax_check_rate']:.2f}% |"
            )
            
        # 2. 查询复杂度分析
        report_content.append("\n### 1.2 查询复杂度分析\n")
        report_content.append("| 模型 | 平均复杂度评分 |")
        report_content.append("|------|----------------|")
        
        for model_name, model_results in results.items():
            # 计算平均复杂度评分
            if model_results['complexity_scores']:
                avg_complexity = sum(model_results['complexity_scores']) / len(model_results['complexity_scores'])
            else:
                avg_complexity = 0
            report_content.append(
                f"| {model_name} | {avg_complexity:.2f} |"
            )
            
        # 3. 结果集质量分析
        report_content.append("\n### 1.3 结果集质量分析\n")
        report_content.append("| 模型 | 精确率 | 召回率 | F1分数 | 结果集大小比 |")
        report_content.append("|------|--------|--------|--------|--------------|")
        
        for model_name, model_results in results.items():
            # 计算平均值
            precision = sum(model_results['result_set_metrics']['precision']) / len(model_results['result_set_metrics']['precision']) if model_results['result_set_metrics']['precision'] else 0
            recall = sum(model_results['result_set_metrics']['recall']) / len(model_results['result_set_metrics']['recall']) if model_results['result_set_metrics']['recall'] else 0
            f1 = sum(model_results['result_set_metrics']['f1_score']) / len(model_results['result_set_metrics']['f1_score']) if model_results['result_set_metrics']['f1_score'] else 0
            size_ratio = sum(model_results['result_set_metrics']['size_ratio']) / len(model_results['result_set_metrics']['size_ratio']) if model_results['result_set_metrics']['size_ratio'] else 0
            
            report_content.append(
                f"| {model_name} | "
                f"{precision:.2f} | "
                f"{recall:.2f} | "
                f"{f1:.2f} | "
                f"{size_ratio:.2f} |"
            )
            
        # 4. 执行效率分析
        report_content.append("\n### 1.4 执行效率分析\n")
        report_content.append("| 模型 | 平均执行时间 (ms) | 平均结果集大小 | 平均执行效率 |")
        report_content.append("|------|------------------|----------------|--------------|")
        
        for model_name, model_results in results.items():
            # 计算平均执行效率
            if model_results['execution_metrics']['efficiency_scores']:
                avg_efficiency = sum(model_results['execution_metrics']['efficiency_scores']) / len(model_results['execution_metrics']['efficiency_scores'])
            else:
                avg_efficiency = 0
                
            report_content.append(
                f"| {model_name} | "
                f"{model_results['execution_metrics']['avg_time']:.2f} | "
                f"{model_results['execution_metrics']['avg_result_size']:.2f} | "
                f"{avg_efficiency:.2f} |"
            )
            
        # 5. 错误分析
        report_content.append("\n### 1.5 错误分析\n")
        report_content.append("| 模型 | 语法错误 | 执行错误 | 结果不匹配 |")
        report_content.append("|------|----------|----------|------------|")
        
        for model_name, model_results in results.items():
            errors = model_results['errors']
            report_content.append(
                f"| {model_name} | "
                f"{errors['syntax']} | "
                f"{errors['execution']} | "
                f"{errors['result_mismatch']} |"
            )
            
        # 保存报告
        report_path = os.path.join(self.output_dir, f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
            
        return report_path 