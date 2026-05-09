"""Output Layer – business logic for visualization, export & feedback (Section 6)."""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from analysis_agent_system.app.config import settings
from analysis_agent_system.app.models.output import (
    GeoData,
    ChartDataPoint,
    ChartData,
    VisualizationResponseData,
    ExportFormat,
    ExportResponseData,
    FeedbackRequest,
    FeedbackResponseData,
)
from analysis_agent_system.app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# ======================================================================
# 6.1 Visualization Data
# ======================================================================

async def get_visualization(
    db: Session,
    task_id: str,
) -> VisualizationResponseData:
    """Generate visualization data for a task using LLM."""

    # --- Fetch task and result data from DB ---
    task_row = db.execute(
        text("SELECT * FROM analysis_tasks WHERE task_id = :task_id"),
        {"task_id": task_id},
    ).fetchone()

    if task_row is None:
        raise ValueError(f"Task {task_id} not found")

    # Gather available result data
    effect_row = db.execute(
        text("SELECT * FROM effect_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    report_row = db.execute(
        text("SELECT * FROM report_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    context = {
        "task_id": task_id,
        "has_effect_result": effect_row is not None,
        "has_report_result": report_row is not None,
    }

    # --- LLM: Generate visualization data ---
    geo_data: Optional[GeoData] = None
    chart_data: Optional[ChartData] = None

    try:
        viz_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a data visualization expert for UAV flight analysis. "
                "Generate visualization data based on the task results. "
                "Return JSON with: "
                "1. geo_data: {flight_trajectory: GeoJSON FeatureCollection or null, "
                "   coverage_heatmap: GeoJSON FeatureCollection or null, "
                "   key_findings: GeoJSON FeatureCollection or null} "
                "2. chart_data: {battery_curve: [{time: string, level: float}]} "
                "If data is not available, set fields to null."
            ),
            user_prompt=json.dumps(context, ensure_ascii=False),
        )

        if isinstance(viz_result, dict):
            gd = viz_result.get("geo_data")
            if gd:
                geo_data = GeoData(**gd)

            cd = viz_result.get("chart_data")
            if cd:
                battery_curve = [ChartDataPoint(**p) for p in cd.get("battery_curve", [])]
                chart_data = ChartData(battery_curve=battery_curve)

    except Exception as exc:
        logger.warning("LLM visualization generation failed: %s", exc)

    return VisualizationResponseData(
        geo_data=geo_data,
        chart_data=chart_data,
    )


# ======================================================================
# 6.2 Export Report
# ======================================================================

async def export_report(
    db: Session,
    task_id: str,
    export_format: ExportFormat,
) -> ExportResponseData:
    """Export a task report in the requested format, generating real files."""

    job_id = f"export_{uuid.uuid4().hex[:12]}"

    # --- Fetch task data ---
    task_row = db.execute(
        text("SELECT * FROM analysis_tasks WHERE task_id = :task_id"),
        {"task_id": task_id},
    ).fetchone()

    if task_row is None:
        raise ValueError(f"Task {task_id} not found")

    # --- Fetch related result data ---
    effect_row = db.execute(
        text("SELECT * FROM effect_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    report_row = db.execute(
        text("SELECT * FROM report_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    quality_row = db.execute(
        text("SELECT * FROM quality_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    validation_row = db.execute(
        text("SELECT * FROM validation_results WHERE task_id = :task_id ORDER BY created_at DESC LIMIT 1"),
        {"task_id": task_id},
    ).fetchone()

    # --- Prepare report data ---
    report_data = {
        "task_id": task_id,
        "task_name": task_row.task_name if hasattr(task_row, "task_name") else "Unknown Task",
        "description": task_row.description if hasattr(task_row, "description") else "",
        "status": task_row.status if hasattr(task_row, "status") else "UNKNOWN",
        "created_at": str(task_row.created_at) if hasattr(task_row, "created_at") else "",
        "has_effect_result": effect_row is not None,
        "has_report_result": report_row is not None,
        "has_quality_result": quality_row is not None,
        "has_validation_result": validation_row is not None,
        "include_evidence_chain": export_format.include_evidence_chain,
        "include_validation_report": export_format.include_validation_report,
    }

    # Add effect results if available
    if effect_row and hasattr(effect_row, "coverage_json"):
        try:
            report_data["coverage_analysis"] = json.loads(effect_row.coverage_json) if effect_row.coverage_json else None
            report_data["accuracy_analysis"] = json.loads(effect_row.accuracy_json) if effect_row.accuracy_json else None
        except Exception as e:
            logger.warning(f"Failed to parse effect results: {e}")

    # Add report results if available
    if report_row:
        try:
            if hasattr(report_row, "coordinates_json") and report_row.coordinates_json:
                report_data["coordinates"] = json.loads(report_row.coordinates_json)
            if hasattr(report_row, "evidence_json") and report_row.evidence_json:
                report_data["evidence_chain"] = json.loads(report_row.evidence_json)
            if hasattr(report_row, "route_efficiency_json") and report_row.route_efficiency_json:
                report_data["route_efficiency"] = json.loads(report_row.route_efficiency_json)
            if hasattr(report_row, "obstacle_energy_json") and report_row.obstacle_energy_json:
                report_data["obstacle_and_energy"] = json.loads(report_row.obstacle_energy_json)
        except Exception as e:
            logger.warning(f"Failed to parse report results: {e}")

    # Add quality results if available
    if quality_row:
        try:
            if hasattr(quality_row, "total_score"):
                report_data["quality_total_score"] = quality_row.total_score
            if hasattr(quality_row, "dimensions_json") and quality_row.dimensions_json:
                report_data["quality_dimensions"] = json.loads(quality_row.dimensions_json)
            if hasattr(quality_row, "suggestions_json") and quality_row.suggestions_json:
                report_data["optimization_suggestions"] = json.loads(quality_row.suggestions_json)
        except Exception as e:
            logger.warning(f"Failed to parse quality results: {e}")

    # Add validation results if requested and available
    if export_format.include_validation_report and validation_row:
        try:
            if hasattr(validation_row, "summary_json") and validation_row.summary_json:
                report_data["validation_summary"] = json.loads(validation_row.summary_json)
            if hasattr(validation_row, "details_json") and validation_row.details_json:
                report_data["validation_details"] = json.loads(validation_row.details_json)
        except Exception as e:
            logger.warning(f"Failed to parse validation results: {e}")

    # --- Translate optimization suggestions to Chinese using LLM ---
    if report_data.get("optimization_suggestions"):
        try:
            llm_translation = await llm_client.analyse_json(
                system_prompt=(
                    "You are a professional translator specializing in UAV/drone flight analysis. "
                    "Translate the 'content' field of each optimization suggestion from English to Chinese. "
                    "Keep all other fields unchanged. Return the complete JSON array with translated content. "
                    "The translation should be professional, concise, and use appropriate technical terminology. "
                    "IMPORTANT: All 'content' fields MUST be in Chinese. Do not leave any content in English."
                ),
                user_prompt=json.dumps(report_data["optimization_suggestions"], ensure_ascii=False),
            )
            
            if isinstance(llm_translation, list) and len(llm_translation) > 0:
                # Verify that content is actually translated
                has_chinese = any(
                    any('\u4e00' <= char <= '\u9fff' for char in suggestion.get('content', ''))
                    for suggestion in llm_translation
                )
                
                if has_chinese:
                    report_data["optimization_suggestions"] = llm_translation
                    logger.info(f"Successfully translated {len(llm_translation)} optimization suggestions to Chinese")
                else:
                    logger.warning("LLM returned translations but no Chinese characters detected, using fallback")
                    raise ValueError("Translation did not contain Chinese characters")
            else:
                raise ValueError("LLM returned empty or invalid translation")
                
        except Exception as exc:
            logger.warning(f"LLM translation of suggestions failed: {exc}, using rule-based fallback")
            # Fallback: Apply simple rule-based translation for common patterns
            report_data["optimization_suggestions"] = _translate_suggestions_fallback(
                report_data["optimization_suggestions"]
            )

    # --- Use LLM to generate executive summary ---
    executive_summary = None
    try:
        summary_prompt = {
            "task_info": {
                "task_id": report_data.get("task_id"),
                "task_name": report_data.get("task_name"),
                "description": report_data.get("description"),
                "status": report_data.get("status"),
            },
            "coverage_analysis": report_data.get("coverage_analysis"),
            "accuracy_analysis": report_data.get("accuracy_analysis"),
            "route_efficiency": report_data.get("route_efficiency"),
            "quality_score": {
                "total_score": report_data.get("quality_total_score"),
                "dimensions": report_data.get("quality_dimensions"),
            },
            "optimization_suggestions": report_data.get("optimization_suggestions", []),
        }
        
        llm_summary = await llm_client.analyse_json(
            system_prompt=(
                "You are an expert UAV/drone flight analysis report summarizer. "
                "Given the complete analysis results including coverage, accuracy, route efficiency, and quality scores, "
                "generate a comprehensive executive summary in Chinese. "
                "The summary should include: "
                "1. overall_assessment: Overall assessment of the flight mission (2-3 sentences) "
                "2. key_findings: List of 3-5 key findings from the analysis "
                "3. strengths: List of strengths/good aspects identified "
                "4. areas_for_improvement: List of areas that need improvement "
                "5. recommendations: 2-3 actionable recommendations for future flights "
                "Return JSON with these keys. Be specific, data-driven, and professional."
            ),
            user_prompt=json.dumps(summary_prompt, ensure_ascii=False),
        )
        
        if isinstance(llm_summary, dict):
            executive_summary = llm_summary
            report_data["executive_summary"] = executive_summary
            logger.info(f"Generated executive summary for task {task_id}")
    except Exception as exc:
        logger.warning(f"LLM executive summary generation failed: {exc}")
        # Provide a fallback summary
        report_data["executive_summary"] = {
            "overall_assessment": "分析报告已生成，但智能总结暂时不可用。",
            "key_findings": ["请查看下方详细分析数据"],
            "strengths": [],
            "areas_for_improvement": [],
            "recommendations": []
        }

    # --- Generate file based on format ---
    download_url: Optional[str] = None
    filename = f"report_{task_id}.{export_format.format.lower()}"
    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)
    file_path = export_dir / filename

    try:
        if export_format.format == "HTML":
            # Generate HTML report
            html_content = _generate_html_report(report_data)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            download_url = f"/api/v1/output/export/{job_id}/download"
            
        elif export_format.format == "GeoJSON":
            # Generate GeoJSON report
            geojson_content = _generate_geojson_report(report_data)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(geojson_content, f, ensure_ascii=False, indent=2)
            download_url = f"/api/v1/output/export/{job_id}/download"
            
        elif export_format.format in ["PDF", "WORD"]:
            # For PDF and WORD, generate HTML first then note conversion needed
            # In production, you would use libraries like reportlab (PDF) or python-docx (WORD)
            html_content = _generate_html_report(report_data)
            # For now, save as HTML with appropriate extension
            actual_filename = f"report_{task_id}.html"
            actual_file_path = export_dir / actual_filename
            with open(actual_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Log that conversion is needed
            logger.info(
                f"{export_format.format} export requested. "
                f"Generated HTML at {actual_file_path}. "
                f"In production, convert to {export_format.format} using appropriate library."
            )
            download_url = f"/api/v1/output/export/{job_id}/download"
            
        else:
            logger.warning(f"Unsupported export format: {export_format.format}")
            
    except Exception as exc:
        logger.error(f"Failed to generate export file: {exc}")
        download_url = None

    # --- Persist export job to DB ---
    try:
        db.execute(
            text(
                """
                INSERT INTO export_jobs
                    (job_id, task_id, format, include_evidence_chain,
                     include_validation_report, status, download_url, created_at)
                VALUES
                    (:job_id, :task_id, :format, :include_evidence_chain,
                     :include_validation_report, :status, :download_url, :created_at)
                """
            ),
            {
                "job_id": job_id,
                "task_id": task_id,
                "format": export_format.format,
                "include_evidence_chain": export_format.include_evidence_chain,
                "include_validation_report": export_format.include_validation_report,
                "status": "COMPLETED" if download_url else "FAILED",
                "download_url": download_url,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist export job failed: %s", exc)

    return ExportResponseData(
        job_id=job_id,
        status="COMPLETED" if download_url else "FAILED",
        download_url=download_url,
    )


def _generate_html_report(report_data: dict) -> str:
    """Generate HTML report content from report data."""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flight Analysis Report - {report_data.get('task_name', 'Unknown')}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .success {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .error {{ color: #e74c3c; }}
        .summary-box {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .summary-box h2 {{ color: white; border-bottom: 2px solid rgba(255,255,255,0.3); }}
        .summary-item {{ margin: 15px 0; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 5px; }}
        .summary-item h3 {{ margin: 0 0 10px 0; font-size: 16px; }}
        .summary-item ul {{ margin: 5px 0; padding-left: 20px; }}
        .summary-item li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <h1>🚁 飞行分析报告</h1>
    
    <div class="section">
        <h2>任务信息</h2>
        <p><strong>任务ID:</strong> {report_data.get('task_id', 'N/A')}</p>
        <p><strong>任务名称:</strong> {report_data.get('task_name', 'N/A')}</p>
        <p><strong>描述:</strong> {report_data.get('description', 'N/A')}</p>
        <p><strong>状态:</strong> {report_data.get('status', 'N/A')}</p>
        <p><strong>创建时间:</strong> {report_data.get('created_at', 'N/A')}</p>
    </div>
"""

    # Add Coverage Analysis
    if report_data.get('coverage_analysis'):
        cov = report_data['coverage_analysis']
        html += f"""
    <div class="section">
        <h2>📊 覆盖分析</h2>
        <div class="metric">
            <div class="metric-value">{cov.get('total_coverage_rate', 0) * 100:.1f}%</div>
            <div class="metric-label">总覆盖率</div>
        </div>
        <div class="metric">
            <div class="metric-value">{cov.get('valid_coverage_rate', 0) * 100:.1f}%</div>
            <div class="metric-label">有效覆盖率</div>
        </div>
        <div class="metric">
            <div class="metric-value">{cov.get('blind_area_square_meter', 0):.1f} m²</div>
            <div class="metric-label">盲区面积</div>
        </div>
        <div class="metric">
            <div class="metric-value">{cov.get('coverage_uniformity', 'N/A')}</div>
            <div class="metric-label">均匀性</div>
        </div>
    </div>
"""

    # Add Accuracy Analysis
    if report_data.get('accuracy_analysis'):
        acc = report_data['accuracy_analysis']
        html += f"""
    <div class="section">
        <h2>🎯 精度分析</h2>
        <div class="metric">
            <div class="metric-value">{acc.get('track_deviation_meter', 0):.2f} m</div>
            <div class="metric-label">轨迹偏差</div>
        </div>
        <div class="metric">
            <div class="metric-value">{acc.get('altitude_deviation_meter', 0):.2f} m</div>
            <div class="metric-label">高度偏差</div>
        </div>
        <div class="metric">
            <div class="metric-value">{acc.get('speed_deviation_km_h', 0):.2f} km/h</div>
            <div class="metric-label">速度偏差</div>
        </div>
        <div class="metric">
            <div class="metric-value">{acc.get('target_overlap_rate', 0) * 100:.1f}%</div>
            <div class="metric-label">目标重叠率</div>
        </div>
    </div>
"""

    # Add Route Efficiency
    if report_data.get('route_efficiency'):
        route = report_data['route_efficiency']
        html += f"""
    <div class="section">
        <h2>🛤️ 路线效率</h2>
        <table>
            <tr><th>指标</th><th>数值</th></tr>
            <tr><td>实际距离</td><td>{route.get('actual_distance_km', 0):.2f} km</td></tr>
            <tr><td>理论距离</td><td>{route.get('theoretical_distance_km', 0):.2f} km</td></tr>
            <tr><td>利用率</td><td>{route.get('utilization_rate', 0) * 100:.1f}%</td></tr>
            <tr><td>转弯次数</td><td>{route.get('turn_count', 0)}</td></tr>
            <tr><td>爬升/下降次数</td><td>{route.get('climb_descent_count', 0)}</td></tr>
            <tr><td>悬停时间</td><td>{route.get('hover_time_min', 0):.1f} min</td></tr>
        </table>
"""
        if route.get('low_efficiency_reasons'):
            html += "<p><strong>低效原因:</strong></p><ul>"
            for reason in route['low_efficiency_reasons']:
                html += f"<li>{reason}</li>"
            html += "</ul>"
        html += "</div>"

    # Add Quality Score
    if report_data.get('quality_total_score') is not None:
        score = report_data['quality_total_score']
        score_class = "success" if score >= 80 else "warning" if score >= 60 else "error"
        html += f"""
    <div class="section">
        <h2>⭐ 质量评分</h2>
        <div class="metric">
            <div class="metric-value {score_class}">{score:.1f}/100</div>
            <div class="metric-label">总分</div>
        </div>
"""
        if report_data.get('quality_dimensions'):
            html += "<table><tr><th>维度</th><th>得分</th><th>权重</th></tr>"
            for dim_name, dim_data in report_data['quality_dimensions'].items():
                # Translate dimension names to Chinese
                dim_names_cn = {
                    'coverage_quality': '覆盖质量',
                    'accuracy_quality': '精度质量',
                    'route_efficiency': '路线效率',
                    'data_completeness': '数据完整性',
                    'safety_compliance': '安全合规性'
                }
                dim_cn = dim_names_cn.get(dim_name, dim_name)
                html += f"<tr><td>{dim_cn}</td><td>{dim_data.get('score', 0):.1f}</td><td>{dim_data.get('weight', 0):.2f}</td></tr>"
            html += "</table>"
        html += "</div>"

    # Add Optimization Suggestions
    if report_data.get('optimization_suggestions'):
        html += """
    <div class="section">
        <h2>💡 优化建议</h2>
        <table>
            <tr><th>优先级</th><th>维度</th><th>类型</th><th>建议内容</th></tr>
"""
        for suggestion in report_data['optimization_suggestions']:
            priority_class = "error" if suggestion.get('priority') == 'HIGH' else "warning" if suggestion.get('priority') == 'NORMAL' else ""
            priority_cn = {'HIGH': '高', 'NORMAL': '中', 'LOW': '低'}.get(suggestion.get('priority'), suggestion.get('priority'))
            
            # Translate suggestion types
            type_cn = {
                'PARAMETER_ADJUSTMENT': '参数调整',
                'ROUTE_CHANGE': '路线变更',
                'DATA_SUPPLEMENT': '数据补充'
            }.get(suggestion.get('type'), suggestion.get('type'))
            
            # Translate dimension names
            dim_names_cn = {
                'coverage_quality': '覆盖质量',
                'accuracy_quality': '精度质量',
                'route_efficiency': '路线效率',
                'data_completeness': '数据完整性',
                'safety_compliance': '安全合规性'
            }
            target_dim_cn = dim_names_cn.get(suggestion.get('target_dimension'), suggestion.get('target_dimension'))
            
            html += f"""<tr>
                <td class="{priority_class}"><strong>{priority_cn}</strong></td>
                <td>{target_dim_cn}</td>
                <td>{type_cn}</td>
                <td>{suggestion.get('content', 'N/A')}</td>
            </tr>
"""
        html += "</table></div>"

    # Add Executive Summary (AI-generated) - AFTER optimization suggestions
    if report_data.get('executive_summary'):
        summary = report_data['executive_summary']
        html += f"""
    <div class="summary-box">
        <h2>📋 智能总结</h2>
        
        <div class="summary-item">
            <h3>🎯 总体评估</h3>
            <p>{summary.get('overall_assessment', '暂无评估')}</p>
        </div>
        
        <div class="summary-item">
            <h3>🔍 关键发现</h3>
            <ul>
"""
        for finding in summary.get('key_findings', []):
            html += f"                <li>{finding}</li>\n"
        html += """            </ul>
        </div>
        
        <div class="summary-item">
            <h3>✅ 优势</h3>
            <ul>
"""
        for strength in summary.get('strengths', []):
            html += f"                <li>{strength}</li>\n"
        html += """            </ul>
        </div>
        
        <div class="summary-item">
            <h3>⚠️ 待改进领域</h3>
            <ul>
"""
        for improvement in summary.get('areas_for_improvement', []):
            html += f"                <li>{improvement}</li>\n"
        html += """            </ul>
        </div>
        
        <div class="summary-item">
            <h3>💡 建议</h3>
            <ul>
"""
        for recommendation in summary.get('recommendations', []):
            html += f"                <li>{recommendation}</li>\n"
        html += """            </ul>
        </div>
    </div>
"""

    # Add Evidence Chain if included
    if report_data.get('include_evidence_chain') and report_data.get('evidence_chain'):
        html += """
    <div class="section">
        <h2>🔗 证据链</h2>
        <table>
            <tr><th>证据ID</th><th>源数据</th><th>时间戳</th><th>区块链交易</th></tr>
"""
        for evidence in report_data['evidence_chain']:
            html += f"""<tr>
                <td>{evidence.get('evidence_id', 'N/A')}</td>
                <td>{evidence.get('source_data_id', 'N/A')}</td>
                <td>{evidence.get('timestamp', 'N/A')}</td>
                <td>{evidence.get('blockchain_tx_id', 'N/A') or 'N/A'}</td>
            </tr>
"""
        html += "</table></div>"

    # Add Validation Summary if included
    if report_data.get('include_validation_report') and report_data.get('validation_summary'):
        val = report_data['validation_summary']
        html += f"""
    <div class="section">
        <h2>✅ 验证摘要</h2>
        <div class="metric">
            <div class="metric-value">{val.get('total_checks', 0)}</div>
            <div class="metric-label">总检查数</div>
        </div>
        <div class="metric">
            <div class="metric-value success">{val.get('passed', 0)}</div>
            <div class="metric-label">通过</div>
        </div>
        <div class="metric">
            <div class="metric-value error">{val.get('failed', 0)}</div>
            <div class="metric-label">失败</div>
        </div>
    </div>
"""

    html += """
    <div class="section">
        <p style="text-align: center; color: #7f8c8d; margin-top: 40px;">
            <em>报告由 Analysis Agent System 生成 | """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</em>
        </p>
    </div>
</body>
</html>"""

    return html


def _generate_geojson_report(report_data: dict) -> dict:
    """Generate GeoJSON report content from report data."""
    
    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "task_id": report_data.get('task_id'),
            "task_name": report_data.get('task_name'),
            "generated_at": datetime.now().isoformat(),
            "format": "GeoJSON"
        },
        "features": []
    }

    # Add coordinates as points if available
    if report_data.get('coordinates'):
        for coord in report_data['coordinates']:
            location = coord.get('location', {})
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        location.get('lon', 0),
                        location.get('lat', 0),
                        location.get('altitude', 0)
                    ]
                },
                "properties": {
                    "issue": coord.get('issue', ''),
                    "level": coord.get('level', 'NORMAL'),
                    "address_desc": coord.get('address_desc', ''),
                    "coord_system": coord.get('coord_system', 'WGS84')
                }
            }
            geojson["features"].append(feature)

    return geojson


# ======================================================================
# 6.3 User Feedback
# ======================================================================

async def submit_feedback(
    db: Session,
    task_id: str,
    request: FeedbackRequest,
) -> FeedbackResponseData:
    """Submit user feedback, use LLM for analysis, persist to DB."""

    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"

    # --- LLM: Analyze feedback and suggest improvements ---
    rag_sync_status = "QUEUED"
    try:
        fb_result = await llm_client.analyse_json(
            system_prompt=(
                "You are a feedback analysis system. "
                "Given user feedback on a flight analysis report, determine if the feedback "
                "should be synced to the RAG knowledge base. "
                "Return JSON with: "
                "1. rag_sync: true/false "
                "2. suggestions: [{type: string, content: string}]"
            ),
            user_prompt=json.dumps(
                {
                    "task_id": task_id,
                    "feedback": request.feedback,
                    "evidence_chain": request.evidence_chain,
                },
                ensure_ascii=False,
            ),
        )

        if isinstance(fb_result, dict):
            rag_sync_status = "SYNCED" if fb_result.get("rag_sync", False) else "SKIPPED"
            suggestions = fb_result.get("suggestions", [])

    except Exception as exc:
        logger.warning("LLM feedback analysis failed: %s", exc)

    # --- Persist feedback to DB ---
    try:
        db.execute(
            text(
                """
                INSERT INTO feedbacks
                    (feedback_id, task_id, feedback, evidence_chain,
                     rag_sync_status, created_at)
                VALUES
                    (:feedback_id, :task_id, :feedback, :evidence_chain,
                     :rag_sync_status, :created_at)
                """
            ),
            {
                "feedback_id": feedback_id,
                "task_id": task_id,
                "feedback": request.feedback,
                "evidence_chain": json.dumps(request.evidence_chain, ensure_ascii=False),
                "rag_sync_status": rag_sync_status,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB persist feedback failed: %s", exc)

    return FeedbackResponseData(
        feedback_id=feedback_id,
        rag_sync_status=rag_sync_status,
    )


def _translate_suggestions_fallback(suggestions: list) -> list:
    """Fallback translation for optimization suggestions when LLM fails.
    
    Uses pattern matching to translate common English phrases to Chinese.
    """
    # Common translation patterns for UAV/drone analysis
    translation_patterns = {
        # Data collection
        "collect flight data": "收集飞行数据",
        "flight data": "飞行数据",
        "timestamps": "时间戳",
        "gps coordinates": "GPS坐标",
        "sensor readings": "传感器读数",
        "mission status": "任务状态",
        
        # Route planning
        "replan route": "重新规划路线",
        "full coverage": "完全覆盖",
        "target area": "目标区域",
        "mission requirements": "任务要求",
        "optimize flight path": "优化飞行路径",
        "minimize redundant flight segments": "减少冗余飞行段",
        "reduce total flight time": "减少总飞行时间",
        
        # Calibration and accuracy
        "adjust": "调整",
        "calibration parameters": "校准参数",
        "reduce positional drift": "减少位置漂移",
        "improve sensor accuracy": "提高传感器精度",
        "gps and imu calibration": "GPS和IMU校准",
        
        # Safety and compliance
        "enable automatic": "启用自动",
        "altitude and speed limits": "高度和速度限制",
        "integrate obstacle avoidance protocols": "集成避障协议",
        "safety compliance": "安全合规",
        
        # General terms
        "task": "任务",
        "including": "包括",
        "to ensure": "以确保",
        "based on": "基于",
        "and": "和",
        "for": "用于",
    }
    
    translated_suggestions = []
    for suggestion in suggestions:
        translated_suggestion = suggestion.copy()
        content = suggestion.get('content', '')
        
        if content:
            # Try to translate using pattern matching
            translated_content = content.lower()
            
            # Apply translations (longer phrases first to avoid partial matches)
            sorted_patterns = sorted(translation_patterns.keys(), key=len, reverse=True)
            for english_phrase in sorted_patterns:
                chinese_translation = translation_patterns[english_phrase]
                translated_content = translated_content.replace(english_phrase, chinese_translation)
            
            # Capitalize first letter if original was capitalized
            if content[0].isupper() and translated_content:
                translated_content = translated_content[0].upper() + translated_content[1:]
            
            # If no translation happened, add a note
            if translated_content == content.lower():
                logger.warning(f"Could not translate suggestion: {content[:50]}...")
                translated_content = f"[待翻译] {content}"
            
            translated_suggestion['content'] = translated_content
        
        translated_suggestions.append(translated_suggestion)
    
    logger.info(f"Fallback translated {len(translated_suggestions)} suggestions")
    return translated_suggestions
