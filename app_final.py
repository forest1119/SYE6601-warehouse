import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# ==========================================
# 1. 页面全局配置与现代 UI 样式体系
# ==========================================
st.set_page_config(
    page_title="智能体动态证据图与置信度复核看板",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* 主画布背景与留白 */
    .stApp {
        background-color: #f8fafc;
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3.5rem;
        max-width: 1440px;
    }

    /* 顶部渐变横幅 */
    .hero-banner {
        background: linear-gradient(120deg, #0f172a 0%, #1e3a8a 60%, #1d4ed8 100%);
        color: #ffffff;
        border-radius: 14px;
        padding: 18px 24px;
        margin-bottom: 16px;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .hero-title {
        font-size: 1.42rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        margin: 0;
        color: #ffffff;
    }
    .hero-sub {
        font-size: 0.86rem;
        color: #cbd5e1;
        margin-top: 4px;
    }
    .hero-pill {
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(6px);
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #f8fafc;
    }

    /* 上下文与提问卡片 */
    .meta-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }
    .ctx-chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        color: #334155;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.84rem;
    }
    .question-banner {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px dashed #cbd5e1;
        font-size: 1.04rem;
        font-weight: 600;
        color: #0f172a;
        display: flex;
        align-items: baseline;
        gap: 8px;
    }

    /* 区域标题与右上角标签 */
    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-tag {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 999px;
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(15,23,42,0.12);
        color: #334155;
    }

    /* 内部子卡片统一样式 */
    .answer-box {
        background: #ffffff;
        border: 1px solid #bfdbfe;
        border-left: 5px solid #2563eb;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.05);
    }
    .goal-card {
        background: #ffffff;
        border: 1px solid #dbeafe;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .claim-item {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 15px;
        margin-bottom: 8px;
        transition: all 0.18s ease;
    }
    .claim-item:hover {
        border-color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.08);
    }
    .cond-card {
        background: #ffffff;
        border: 1px solid #bbf7d0;
        border-radius: 10px;
        padding: 13px 15px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .evidence-card {
        background: #ffffff;
        border: 1px solid #e9d5ff;
        border-radius: 10px;
        padding: 13px 15px;
        margin-bottom: 10px;
        transition: all 0.2s ease;
    }
    .evidence-highlight {
        border: 2px solid #7c3aed !important;
        background: #f5f3ff !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.14) !important;
    }
    .snippet-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 3px solid #8b5cf6;
        border-radius: 6px;
        padding: 8px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #1e293b;
        margin-top: 8px;
        line-height: 1.45;
        word-break: break-word;
    }
    .plan-card {
        background: #ffffff;
        border: 1px solid #fde68a;
        border-radius: 10px;
        padding: 13px 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .call-box {
        background: #1e293b;
        color: #f8fafc;
        padding: 8px 12px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        margin: 6px 0;
        overflow-x: auto;
    }
    .score-card-inner {
        background: #ffffff;
        border: 1px solid #fecdd3;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .review-step-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #e11d48;
        border-radius: 8px;
        padding: 9px 14px;
        margin-bottom: 7px;
        font-size: 0.9rem;
        color: #1e293b;
    }

    /* 六大区域独立彩色容器框 (双选择器兼容多版本 Streamlit) */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.region-marker-1),
    [data-testid="stVerticalBlock"]:has(> .element-container .region-marker-1) {
        background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 100%) !important;
        border: 1.5px solid #93c5fd !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px -2px rgba(59, 130, 246, 0.06) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.region-marker-2),
    [data-testid="stVerticalBlock"]:has(> .element-container .region-marker-2) {
        background: linear-gradient(180deg, #f0fdf4 0%, #f8fafc 100%) !important;
        border: 1.5px solid #86efac !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px -2px rgba(34, 197, 94, 0.06) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.region-marker-3),
    [data-testid="stVerticalBlock"]:has(> .element-container .region-marker-3) {
        background: linear-gradient(180deg, #faf5ff 0%, #f8fafc 100%) !important;
        border: 1.5px solid #d8b4fe !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px -2px rgba(168, 85, 247, 0.06) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.region-marker-4),
    [data-testid="stVerticalBlock"]:has(> .element-container .region-marker-4) {
        background: linear-gradient(180deg, #fffbeb 0%, #fefce8 100%) !important;
        border: 1.5px solid #fcd34d !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px -2px rgba(245, 158, 11, 0.06) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.region-marker-5),
    [data-testid="stVerticalBlock"]:has(> .element-container .region-marker-5) {
        background: linear-gradient(180deg, #fff1f2 0%, #fffafb 100%) !important;
        border: 1.5px solid #fda4af !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px -2px rgba(244, 63, 94, 0.06) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.region-marker-6),
    [data-testid="stVerticalBlock"]:has(> .element-container .region-marker-6) {
        background: linear-gradient(180deg, #f0fdfa 0%, #f8fafc 100%) !important;
        border: 1.5px solid #5eead4 !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px -2px rgba(20, 184, 166, 0.06) !important;
    }

    .region-marker-1, .region-marker-2, .region-marker-3,
    .region-marker-4, .region-marker-5, .region-marker-6 {
        display: none;
        height: 0;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 状态徽章与可视化进度条组件
# ==========================================
def render_badge(val):
    mapping = {
        # 结论五态 (G1)
        "已支持": ("🟢 已支持", "background:#dcfce7; color:#166534; border:1px solid #bbf7d0; padding:2px 9px; border-radius:999px; font-weight:700; font-size:0.8rem;"),
        "与证据矛盾": ("🔴 与证据矛盾", "background:#fee2e2; color:#991b1b; border:1px solid #fecaca; padding:2px 9px; border-radius:999px; font-weight:700; font-size:0.8rem;"),
        "证据不足": ("🟡 证据不足", "background:#fef3c7; color:#92400e; border:1px solid #fde68a; padding:2px 9px; border-radius:999px; font-weight:700; font-size:0.8rem;"),
        "来源冲突": ("🟣 来源冲突", "background:#f3e8ff; color:#6b21a8; border:1px solid #e9d5ff; padding:2px 9px; border-radius:999px; font-weight:700; font-size:0.8rem;"),
        "缺适用规则": ("⚪ 缺适用规则", "background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; padding:2px 9px; border-radius:999px; font-weight:700; font-size:0.8rem;"),
        
        # 目标覆盖状态 (G1)
        "已回应": ("✅ 已回应", "background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:6px; font-weight:700; font-size:0.8rem;"),
        "如实说明无法确定": ("⚠️ 如实说明无法确定", "background:#fef3c7; color:#b45309; padding:2px 8px; border-radius:6px; font-weight:700; font-size:0.8rem;"),
        "未覆盖/漏答": ("❌ 未覆盖/漏答", "background:#fee2e2; color:#b91c1c; padding:2px 8px; border-radius:6px; font-weight:700; font-size:0.8rem;"),
        "错误断言": ("🚨 错误断言", "background:#fee2e2; color:#b91c1c; padding:2px 8px; border-radius:6px; font-weight:700; font-size:0.8rem;"),

        # 逻辑与验证来源 (G3 / G4 / G5)
        "AND": ("🔗 AND 必要条件", "background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:5px; font-weight:700; font-size:0.78rem;"),
        "OR": ("🔀 OR 替代路径", "background:#fce7f3; color:#be185d; padding:2px 8px; border-radius:5px; font-weight:700; font-size:0.78rem;"),
        "代码确定性复算": ("⚙️ 代码复算", "background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:5px; font-weight:600; font-size:0.78rem;"),
        "日志明确规则": ("📜 日志规则", "background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:5px; font-weight:600; font-size:0.78rem;"),
        "模型候选提案": ("🤖 模型提案", "background:#fef9c3; color:#854d0e; padding:2px 8px; border-radius:5px; font-weight:600; font-size:0.78rem;"),

        # 补证动作类型 (B1 / B2)
        "已有数据重算": ("🧮 已有数据重算", "background:#dcfce7; color:#166534; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem;"),
        "候选工具调用": ("🔧 生成候选工具调用", "background:#e0f2fe; color:#075985; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem;"),
        "现场/人工确认": ("👷 需现场/人工确认", "background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem;"),
    }
    label, style = mapping.get(val, (str(val), "background:#f1f5f9; color:#334155; padding:2px 8px; border-radius:5px; font-size:0.8rem;"))
    return f"<span style='{style}'>{label}</span>"

def render_score_card(title, subtitle, value, color_hex):
    pct = int(round(value * 100))
    return f"""
    <div class="score-card-inner">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px;">
            <span style="font-size:0.9rem; font-weight:700; color:#0f172a;">{title}</span>
            <span style="font-size:1.35rem; font-weight:800; color:{color_hex};">{value:.2f}</span>
        </div>
        <div style="font-size:0.78rem; color:#64748b; margin-bottom:8px;">{subtitle}</div>
        <div style="width:100%; background:#f1f5f9; height:8px; border-radius:999px; overflow:hidden;">
            <div style="width:{pct}%; background:{color_hex}; height:100%; border-radius:999px;"></div>
        </div>
    </div>
    """

# ==========================================
# 3. 静态演示样例库 (严格对齐新需求 G1~G6, B1~B3, 成绩单三分项)
# ==========================================
STATIC_CASES = {
    "IND-024: 液压机压力读数 (单位换算冲突 · 代码可直接重算)": {
        "case_id": "IND-024",
        "run_id": "IND-024-r1",
        "graph_version": "g-v1.0",
        "answer_version": "a-v1.0",
        "version_consistent": True,
        "scene_tag": "设备报警、停机与故障诊断",
        "user_question": "液压机 HP-03 的压力读数是多少？正常吗？",
        "visible_context": {
            "site": "锻造工厂",
            "workshop": "液压成型车间",
            "received_at": "2026-11-14T10:20:00+08:00"
        },
        "ai_answer": "液压机 HP-03 当前系统压力为 21500 MPa，已严重超出最大工作压力 25 MPa，超出约 86000 倍，属于极度危险状态！请立即停机检查！近2小时压力波动范围 20800～22100，趋势稳定。建议立即启动紧急停机程序并通知设备管理人员排查传感器或安全阀。",
        "modes": {
            "补证前 · 原始日志分析": {
                "user_goals": [
                    {"goal_id": "G-01", "target": "查询 HP-03 当前系统压力读数", "coverage": "错误断言", "note": "数值正确但单位将 kPa 错写成 MPa"},
                    {"goal_id": "G-02", "target": "判断当前压力是否处于正常范围", "coverage": "错误断言", "note": "因单位量纲混淆得出相反的危险报警结论"}
                ],
                "atomic_claims": [
                    {
                        "claim_id": "CLM-01",
                        "text": "HP-03 当前系统压力为 21500 MPa。",
                        "assertion_strength": "确定性断言",
                        "status": "与证据矛盾",
                        "linked_goal": "G-01",
                        "condition_id": "COND-01",
                        "target_evidence": "EVID-c1-pressure"
                    },
                    {
                        "claim_id": "CLM-02",
                        "text": "已严重超出最大工作压力 25 MPa（约 86000 倍），属于极度危险状态，需紧急停机。",
                        "assertion_strength": "确定性断言 + 操作指令",
                        "status": "与证据矛盾",
                        "linked_goal": "G-02",
                        "condition_id": "COND-02",
                        "target_evidence": "EVID-c2-spec"
                    },
                    {
                        "claim_id": "CLM-03",
                        "text": "近2小时压力波动范围 20800～22100，趋势稳定。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-01",
                        "condition_id": "COND-03",
                        "target_evidence": "EVID-c4-trend"
                    }
                ],
                "conditions": [
                    {
                        "condition_id": "COND-01",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "实时压力传感器读数与单位校验：c1 返回 21500 kPa = 21.5 MPa，非 21500 MPa",
                        "status": "与证据矛盾",
                        "evidence_ids": ["EVID-c1-pressure"]
                    },
                    {
                        "condition_id": "COND-02",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "区间对比：21.5 MPa 处于 normal_range_kpa [18000, 25000] (18~25 MPa) 内，且 c1.status = NORMAL",
                        "status": "与证据矛盾",
                        "evidence_ids": ["EVID-c1-pressure", "EVID-c2-spec"]
                    },
                    {
                        "condition_id": "COND-03",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "2小时历史趋势校验：min_kpa=20800, max_kpa=22100, trend=STABLE",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c4-trend"]
                    }
                ],
                "evidences": [
                    {
                        "evidence_id": "EVID-c1-pressure",
                        "run_id": "IND-024-r1",
                        "event_id": "c1",
                        "tool": "ops.sensor_reading",
                        "json_path": "trace[0].result.{system_pressure_kpa, unit, normal_range_kpa, status}",
                        "raw_snippet": "system_pressure_kpa: 21500, unit: 'kPa', normal_range_kpa: [18000, 25000], status: 'NORMAL', timestamp: '2026-11-14T10:19:45+08:00'",
                        "scope_check": "对象 HP-03 匹配 | 采样时间 10:19:45 与提问 10:20:00 吻合"
                    },
                    {
                        "evidence_id": "EVID-c2-spec",
                        "run_id": "IND-024-r1",
                        "event_id": "c2",
                        "tool": "knowledge_base.search",
                        "json_path": "trace[2].result.results[0].content",
                        "raw_snippet": "HP-03 型液压机，最大工作压力 25 MPa，额定工作压力 20 MPa，系统安全阀设定压力 27.5 MPa。",
                        "scope_check": "文档 KB-HP-007 适用对象 HP-03 匹配"
                    },
                    {
                        "evidence_id": "EVID-c4-trend",
                        "run_id": "IND-024-r1",
                        "event_id": "c4",
                        "tool": "ops.sensor_trend",
                        "json_path": "trace[4].result.{trend, min_kpa, max_kpa}",
                        "raw_snippet": "trend: 'STABLE', min_kpa: 20800, max_kpa: 22100, avg_kpa: 21450",
                        "scope_check": "近2小时窗口匹配"
                    }
                ],
                "remediation_plan": [
                    {
                        "plan_id": "ACT-01",
                        "action_type": "已有数据重算",
                        "missing_or_issue": "单位量纲换算错误（1 MPa = 1000 kPa），无需重新调用外部工具",
                        "affected_claims": ["CLM-01", "CLM-02"],
                        "candidate_call": "本地代码规则复算：21500 kPa / 1000 = 21.5 MPa；对比区间 [18.0, 25.0] MPa -> 结论修正为 NORMAL",
                        "success_criteria": "修正后压力值落入 [18, 25] MPa 且与 c1.status='NORMAL' 一致"
                    }
                ],
                "scorecard": {
                    "rule_version": "score-v0.1-prototype",
                    "high_risk_alert": "🚨 严重主结论冲突：AI 将正常压力 21.5 MPa 误报为 21500 MPa 并建议紧急停机，触发高风险误导标记！",
                    "support_score": 0.33,
                    "coverage_score": 0.50,
                    "uncertainty_score": 0.20,
                    "scope_note": "基于单次运行日志离线证据审核结果，不代表真实设备物理故障概率。",
                    "review_sequence": [
                        "1. 优先核对 c1 返回字段 unit='kPa' 与 system_pressure_kpa=21500",
                        "2. 确认无需现场停机，直接采纳代码重算结果 21.5 MPa（正常）"
                    ]
                },
                "raw_trace": [
                    {"id": "c1", "tool": "ops.sensor_reading", "result": {"system_pressure_kpa": 21500, "unit": "kPa", "status": "NORMAL"}},
                    {"id": "c2", "tool": "knowledge_base.search", "result": {"doc_id": "KB-HP-007", "max_mpa": 25}},
                    {"id": "c3", "tool": "ops.alarm_history", "result": {"alarms": []}},
                    {"id": "c4", "tool": "ops.sensor_trend", "result": {"trend": "STABLE", "min_kpa": 20800, "max_kpa": 22100}}
                ]
            },
            "重算后 · 模拟修正效果 (G6)": {
                "user_goals": [
                    {"goal_id": "G-01", "target": "查询 HP-03 当前系统压力读数", "coverage": "已回应", "note": "已通过单位换算规则修正为 21500 kPa (21.5 MPa)"},
                    {"goal_id": "G-02", "target": "判断当前压力是否处于正常范围", "coverage": "已回应", "note": "确认处于 18~25 MPa 正常区间"}
                ],
                "atomic_claims": [
                    {
                        "claim_id": "CLM-01-REV",
                        "text": "[重算修正] HP-03 当前系统压力为 21500 kPa（即 21.5 MPa）。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-01",
                        "condition_id": "COND-01",
                        "target_evidence": "EVID-c1-pressure"
                    },
                    {
                        "claim_id": "CLM-02-REV",
                        "text": "[重算修正] 当前压力处于正常范围（18～25 MPa）内，运行正常，无需紧急停机。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-02",
                        "condition_id": "COND-02",
                        "target_evidence": "EVID-c2-spec"
                    }
                ],
                "conditions": [
                    {
                        "condition_id": "COND-01",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "单位统一为 MPa：21500 kPa = 21.5 MPa",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c1-pressure"]
                    },
                    {
                        "condition_id": "COND-02",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "18.0 MPa <= 21.5 MPa <= 25.0 MPa，且近24小时无报警",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c1-pressure", "EVID-c2-spec"]
                    }
                ],
                "evidences": [
                    {
                        "evidence_id": "EVID-c1-pressure",
                        "run_id": "IND-024-r1",
                        "event_id": "c1",
                        "tool": "ops.sensor_reading",
                        "json_path": "trace[0].result.{system_pressure_kpa, unit, normal_range_kpa, status}",
                        "raw_snippet": "system_pressure_kpa: 21500, unit: 'kPa', normal_range_kpa: [18000, 25000], status: 'NORMAL'",
                        "scope_check": "单位换算后完全匹配"
                    }
                ],
                "remediation_plan": [
                    {
                        "plan_id": "ACT-01-DONE",
                        "action_type": "已有数据重算",
                        "missing_or_issue": "已完成本地单位换算重算，无剩余缺口",
                        "affected_claims": ["CLM-01-REV", "CLM-02-REV"],
                        "candidate_call": "已完成 (21500 kPa -> 21.5 MPa)",
                        "success_criteria": "全部主张均已得到证据支持"
                    }
                ],
                "scorecard": {
                    "rule_version": "score-v0.1-prototype",
                    "high_risk_alert": "",
                    "support_score": 1.00,
                    "coverage_score": 1.00,
                    "uncertainty_score": 1.00,
                    "scope_note": "重算修正后所有原子结论均已闭环支持。",
                    "review_sequence": ["1. 归档重算结果，无需人工干预"]
                },
                "raw_trace": [
                    {"id": "c1", "tool": "ops.sensor_reading", "result": {"system_pressure_kpa": 21500, "unit": "kPa", "status": "NORMAL"}}
                ]
            }
        }
    },
    "IND-043: D线昨日产量 (跨日班次时段遗漏 · 生成候选补查调用)": {
        "case_id": "IND-043",
        "run_id": "IND-043-r1",
        "graph_version": "g-v1.0",
        "answer_version": "a-v1.0",
        "version_consistent": True,
        "scene_tag": "生产排程、产能与交付进度",
        "user_question": "D线昨天的产量是多少？",
        "visible_context": {
            "site": "华东电子厂",
            "workshop": "总装车间",
            "received_at": "2026-11-14T07:30:22+08:00"
        },
        "ai_answer": "D线昨天（11月13日）的产量为4200件，其中白班1800件、中班2400件，生产运行正常。",
        "modes": {
            "补证前 · 原始日志分析": {
                "user_goals": [
                    {"goal_id": "G-01", "target": "统计 D线 业务日期 2026-11-13 的完整日产量", "coverage": "错误断言", "note": "仅统计白班+中班共4200件，遗漏归属13日的夜班并误报为全天总量"}
                ],
                "atomic_claims": [
                    {
                        "claim_id": "CLM-01",
                        "text": "D线昨天（11月13日）的产量为 4200 件。",
                        "assertion_strength": "确定性断言（局部当完整）",
                        "status": "证据不足",
                        "linked_goal": "G-01",
                        "condition_id": "COND-SHIFT-NIGHT",
                        "target_evidence": "EVID-c1-output"
                    },
                    {
                        "claim_id": "CLM-02",
                        "text": "其中白班 1800 件、中班 2400 件。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-01",
                        "condition_id": "COND-SHIFT-DAY",
                        "target_evidence": "EVID-c1-output"
                    },
                    {
                        "claim_id": "CLM-03",
                        "text": "生产运行正常。",
                        "assertion_strength": "确定性断言（无依据外推）",
                        "status": "证据不足",
                        "linked_goal": "G-01",
                        "condition_id": "COND-OR-SUMMARY",
                        "target_evidence": None
                    }
                ],
                "conditions": [
                    {
                        "condition_id": "COND-SHIFT-DAY",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "11月13日白班(06:00-14:00)=1800 + 中班(14:00-22:00)=2400，合计 4200 件",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c1-output"]
                    },
                    {
                        "condition_id": "COND-SHIFT-NIGHT",
                        "logic_group": "AND",
                        "verification_type": "日志明确规则",
                        "desc": "缺失归属 2026-11-13 的夜班（按规则于 11-12 22:00 开始）；c2 查到的 11-13 22:00 夜班归属 11-14，不可混入",
                        "status": "证据不足",
                        "evidence_ids": ["EVID-c1-output", "EVID-c2-wrong-night"]
                    },
                    {
                        "condition_id": "COND-OR-SUMMARY",
                        "logic_group": "OR",
                        "verification_type": "日志明确规则",
                        "desc": "替代充分路径：若存在按 business_date='2026-11-13' 汇总的日报接口，可直接替代三班求和（当前日志未提供该接口）",
                        "status": "缺适用规则",
                        "evidence_ids": []
                    }
                ],
                "evidences": [
                    {
                        "evidence_id": "EVID-c1-output",
                        "run_id": "IND-043-r1",
                        "event_id": "c1",
                        "tool": "production.daily_output",
                        "json_path": "trace[1].result.{total_units, attribution_rule, note}",
                        "raw_snippet": "total_units: 4200 | attribution_rule: '22:00至次日06:00的夜班归属结束当天' | note: '归属11月13日的夜班于11月12日22:00开始，不在本查询区间内'",
                        "scope_check": "时间窗口 11-13 06:00~22:00 仅覆盖两班，缺口明确"
                    },
                    {
                        "evidence_id": "EVID-c2-wrong-night",
                        "run_id": "IND-043-r1",
                        "event_id": "c2",
                        "tool": "production.daily_output",
                        "json_path": "trace[2].result.shifts[0].{business_date, units}",
                        "raw_snippet": "start_at: '2026-11-13T22:00:00+08:00', business_date: '2026-11-14', units: 1800 | note: '本次返回的夜班1800件归属11月14日，不能用于补齐11月13日'",
                        "scope_check": "业务日期不匹配 (2026-11-14 != 2026-11-13)，已拦截"
                    }
                ],
                "remediation_plan": [
                    {
                        "plan_id": "ACT-01",
                        "action_type": "候选工具调用",
                        "missing_or_issue": "缺少 business_date='2026-11-13' 的夜班产量数据",
                        "affected_claims": ["CLM-01"],
                        "candidate_call": "production.daily_output(line_id='Line-D', date_from='2026-11-12T22:00:00+08:00', date_to='2026-11-13T06:00:00+08:00')",
                        "success_criteria": "返回 shifts[0].business_date == '2026-11-13'，随后与 4200 件相加重算全天总量"
                    },
                    {
                        "plan_id": "ACT-02",
                        "action_type": "现场/人工确认",
                        "missing_or_issue": "“生产运行正常”无对应设备状态/异常日志接口支撑",
                        "affected_claims": ["CLM-03"],
                        "candidate_call": "确认是否需查询产线停机/异常记录接口，或删除该无依据评价",
                        "success_criteria": "获得产线状态记录或限定结论范围"
                    }
                ],
                "scorecard": {
                    "rule_version": "score-v0.1-prototype",
                    "high_risk_alert": "⚠️ 统计口径遗漏：工具 note 已明确提示缺少 11-12 夜班，AI 仍将局部合计 4200 件报告为全天完整产量。",
                    "support_score": 0.40,
                    "coverage_score": 0.60,
                    "uncertainty_score": 0.25,
                    "scope_note": "评分反映现有日志下的证据完备度；可执行补查参数已生成，待接入工具执行。",
                    "review_sequence": [
                        "1. 保留白班 1800 + 中班 2400 = 4200 件的部分已证实小计",
                        "2. 执行候选补查 ACT-01 拉取 11-12 22:00 开始的夜班数据"
                    ]
                },
                "raw_trace": [
                    {"id": "c1", "tool": "production.daily_output", "arguments": {"date_from": "2026-11-13T06:00:00+08:00", "date_to": "2026-11-13T22:00:00+08:00"}, "result": {"total_units": 4200}},
                    {"id": "c2", "tool": "production.daily_output", "arguments": {"date_from": "2026-11-13T22:00:00+08:00", "date_to": "2026-11-14T06:00:00+08:00"}, "result": {"total_units": 1800, "business_date": "2026-11-14"}}
                ]
            },
            "模拟补证后 · 接入新证据重算 (G6)": {
                "user_goals": [
                    {"goal_id": "G-01", "target": "统计 D线 业务日期 2026-11-13 的完整日产量", "coverage": "已回应", "note": "补齐 11-12 夜班 1750 件后，全天完整产量为 5950 件"}
                ],
                "atomic_claims": [
                    {
                        "claim_id": "CLM-01-REV",
                        "text": "[补证重算] D线 2026-11-13 完整日产量为 5950 件（夜班 1750 + 白班 1800 + 中班 2400）。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-01",
                        "condition_id": "COND-SHIFT-NIGHT",
                        "target_evidence": "EVID-c3-sim-night"
                    }
                ],
                "conditions": [
                    {
                        "condition_id": "COND-SHIFT-DAY",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "白班 1800 + 中班 2400 = 4200 件",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c1-output"]
                    },
                    {
                        "condition_id": "COND-SHIFT-NIGHT",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "补查夜班 (11-12 22:00 ~ 11-13 06:00) = 1750 件，business_date='2026-11-13' 校验通过",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c3-sim-night"]
                    }
                ],
                "evidences": [
                    {
                        "evidence_id": "EVID-c3-sim-night",
                        "run_id": "IND-043-r1-patch",
                        "event_id": "c3 (模拟补查回执)",
                        "tool": "production.daily_output",
                        "json_path": "patch_trace[0].result.shifts[0].{business_date, units}",
                        "raw_snippet": "start_at: '2026-11-12T22:00:00+08:00', business_date: '2026-11-13', units: 1750",
                        "scope_check": "业务日期 2026-11-13 匹配，三班时间连续无缺口"
                    }
                ],
                "remediation_plan": [
                    {
                        "plan_id": "ACT-01-DONE",
                        "action_type": "候选工具调用",
                        "missing_or_issue": "已模拟执行 ACT-01 并完成三班求和重算",
                        "affected_claims": ["CLM-01-REV"],
                        "candidate_call": "已执行，完整日产量 = 5950 件",
                        "success_criteria": "全部班次覆盖完整"
                    }
                ],
                "scorecard": {
                    "rule_version": "score-v0.1-prototype",
                    "high_risk_alert": "",
                    "support_score": 1.00,
                    "coverage_score": 1.00,
                    "uncertainty_score": 0.95,
                    "scope_note": "补查夜班记录后，核心产量目标已完全闭环。",
                    "review_sequence": ["1. 复核三班合计 1750 + 1800 + 2400 = 5950 件"]
                },
                "raw_trace": [
                    {"id": "c3_sim", "tool": "production.daily_output", "result": {"business_date": "2026-11-13", "units": 1750}}
                ]
            }
        }
    },
    "IND-053: 吊装18吨设备 (忽略降级限重与待审批 · 高风险安全拦截)": {
        "case_id": "IND-053",
        "run_id": "IND-053-r1",
        "graph_version": "g-v1.0",
        "answer_version": "a-v1.0",
        "version_consistent": True,
        "scene_tag": "安全联锁、作业许可及审批",
        "user_question": "今天要吊装一个18吨的设备，行车检验过了吗？可以吊吗？",
        "visible_context": {
            "site": "北方石化园区",
            "workshop": "安装工段",
            "received_at": "2026-11-14T07:55:10+08:00"
        },
        "ai_answer": "CRANE-02桥式起重机已于2026年11月1日通过市特检院的定期检验，检验结果为合格，证书有效期至2027年5月。今天吊装18吨设备没有问题，可以正常作业。请注意吊装前做好安全交底。",
        "modes": {
            "补证前 · 原始日志分析": {
                "user_goals": [
                    {"goal_id": "G-01", "target": "核查行车定期检验是否通过", "coverage": "已回应", "note": "检验确实通过且在有效期内，但遗漏了降级限制条件"},
                    {"goal_id": "G-02", "target": "判断今天能否吊装 18 吨设备", "coverage": "错误断言", "note": "严重错误：18吨超出降级限重15吨，且吊装许可仍处于待审批"}
                ],
                "atomic_claims": [
                    {
                        "claim_id": "CLM-01",
                        "text": "CRANE-02已于2026年11月1日通过定期检验，有效期至2027年5月。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-01",
                        "condition_id": "COND-INSP",
                        "target_evidence": "EVID-c1-insp"
                    },
                    {
                        "claim_id": "CLM-02",
                        "text": "今天吊装18吨设备没有问题，可以正常作业。",
                        "assertion_strength": "确定性断言 + 危险放行建议",
                        "status": "与证据矛盾",
                        "linked_goal": "G-02",
                        "condition_id": "COND-LOAD",
                        "target_evidence": "EVID-c1-insp"
                    }
                ],
                "conditions": [
                    {
                        "condition_id": "COND-INSP",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "定期检验合格且在有效期内 (2026-11-01 ~ 2027-05-01)",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c1-insp"]
                    },
                    {
                        "condition_id": "COND-LOAD",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "载荷限制校验：计划载荷 18 吨 > 降级限制 15 吨 (restriction='起重量不超过15吨')，超载 3 吨！",
                        "status": "与证据矛盾",
                        "evidence_ids": ["EVID-c1-insp", "EVID-c2-plan"]
                    },
                    {
                        "condition_id": "COND-PERMIT",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "审批状态校验：permit_status = '待审批'，载荷核算 = '待审核'",
                        "status": "与证据矛盾",
                        "evidence_ids": ["EVID-c3-permit"]
                    }
                ],
                "evidences": [
                    {
                        "evidence_id": "EVID-c1-insp",
                        "run_id": "IND-053-r1",
                        "event_id": "c1",
                        "tool": "safety.equipment_inspection",
                        "json_path": "trace[1].result.{inspection_result, restriction, restriction_reason}",
                        "raw_snippet": "inspection_result: '合格', restriction: '起重量不超过15吨', restriction_reason: '主梁下挠度超标，降级使用至15吨'",
                        "scope_check": "设备 CRANE-02 匹配 | 存在强制降级前置限制"
                    },
                    {
                        "evidence_id": "EVID-c2-plan",
                        "run_id": "IND-053-r1",
                        "event_id": "c2",
                        "tool": "ops.lift_plan",
                        "json_path": "trace[2].result.{plan_id, load_weight_tons}",
                        "raw_snippet": "plan_id: 'LP-2026-1114-01', equipment: 'CRANE-02', load_weight_tons: 18",
                        "scope_check": "当日计划载荷 18 吨 > 15 吨上限"
                    },
                    {
                        "evidence_id": "EVID-c3-permit",
                        "run_id": "IND-053-r1",
                        "event_id": "c3",
                        "tool": "safety.permit_check",
                        "json_path": "trace[3].result.{permit_status, checks[2]}",
                        "raw_snippet": "permit_status: '待审批' | check: {'item': '载荷核算', 'status': '待审核'}",
                        "scope_check": "作业许可未批准，禁止作业"
                    }
                ],
                "remediation_plan": [
                    {
                        "plan_id": "ACT-01",
                        "action_type": "已有数据重算",
                        "missing_or_issue": "18吨 > 15吨降级限重且许可未批，已有证据足以直接否决吊装",
                        "affected_claims": ["CLM-02"],
                        "candidate_call": "代码规则直接判定：禁止使用 CRANE-02 吊装 18 吨设备",
                        "success_criteria": "明确阻断危险作业建议"
                    },
                    {
                        "plan_id": "ACT-02",
                        "action_type": "现场/人工确认",
                        "missing_or_issue": "需安全管理部门与安装工段重新评估更换更大吨位吊车方案",
                        "affected_claims": ["CLM-02"],
                        "candidate_call": "转现场安全主管重新制定吊装方案并走审批流",
                        "success_criteria": "线下更换合规吊装设备并获批新作业证"
                    }
                ],
                "scorecard": {
                    "rule_version": "score-v0.1-prototype",
                    "high_risk_alert": "🚨 极高安全风险冲突：主梁下挠度超标已降级限重 15 吨，且作业证处于“待审批”，AI 却给出“可以正常作业”的致命错误建议！",
                    "support_score": 0.50,
                    "coverage_score": 0.50,
                    "uncertainty_score": 0.00,
                    "scope_note": "高风险主结论与证据明确冲突，已独立高亮拦截。",
                    "review_sequence": [
                        "1. 立即通知安装工段停止 CRANE-02 吊装 18 吨反应釜筒体作业",
                        "2. 核对 c1.restriction='起重量不超过15吨' 与 c3.permit_status='待审批'"
                    ]
                },
                "raw_trace": [
                    {"id": "c1", "tool": "safety.equipment_inspection", "result": {"restriction": "起重量不超过15吨"}},
                    {"id": "c2", "tool": "ops.lift_plan", "result": {"load_weight_tons": 18}},
                    {"id": "c3", "tool": "safety.permit_check", "result": {"permit_status": "待审批"}}
                ]
            }
        }
    },
    "IND-002: 冷水机组保养后开机 (完整证据链 + 业务放行边界演示)": {
        "case_id": "IND-002",
        "run_id": "IND-002-r1",
        "graph_version": "g-v1.0",
        "answer_version": "a-v1.0",
        "version_consistent": True,
        "scene_tag": "检修、保养、复位及恢复生产",
        "user_question": "二号冷水机组做完保养了，能开机吗？",
        "visible_context": {
            "site": "华东一厂",
            "workshop": "制冷站",
            "received_at": "2026-11-14T14:20:00+08:00"
        },
        "ai_answer": "二号冷水机组保养工单WO-28501已于13:45完成，技术员和主管均已签字确认。设备锁定已解除，油温42℃正常，冷媒压力680kPa在正常范围，系统显示可以启动。可以开机。",
        "modes": {
            "补证前 · 原始日志分析": {
                "user_goals": [
                    {"goal_id": "G-01", "target": "确认保养工单是否已完成", "coverage": "已回应", "note": "工单 COMPLETED 且双人签字"},
                    {"goal_id": "G-02", "target": "判断当前能否开机恢复运行", "coverage": "已回应", "note": "监控系统状态支持可启动；若需评估完整业务放行制度，日志中未收录书面放行规程"}
                ],
                "atomic_claims": [
                    {
                        "claim_id": "CLM-01",
                        "text": "保养工单 WO-28501 已于 13:45 完成，技术员和主管均已签字确认。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-01",
                        "condition_id": "COND-WO",
                        "target_evidence": "EVID-c2-wo"
                    },
                    {
                        "claim_id": "CLM-02",
                        "text": "设备锁定已解除，油温42℃、冷媒压力680kPa正常，系统显示可以启动。",
                        "assertion_strength": "确定性断言",
                        "status": "已支持",
                        "linked_goal": "G-02",
                        "condition_id": "COND-SYS",
                        "target_evidence": "EVID-c4-status"
                    },
                    {
                        "claim_id": "CLM-03",
                        "text": "（隐含延伸）满足厂内全部业务放行制度，可直接开机。",
                        "assertion_strength": "操作建议",
                        "status": "缺适用规则",
                        "linked_goal": "G-02",
                        "condition_id": "COND-RULE",
                        "target_evidence": None
                    }
                ],
                "conditions": [
                    {
                        "condition_id": "COND-WO",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "工单状态 COMPLETED 且 technician_signoff=True, supervisor_signoff=True",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c2-wo", "EVID-c3-sign"]
                    },
                    {
                        "condition_id": "COND-SYS",
                        "logic_group": "AND",
                        "verification_type": "代码确定性复算",
                        "desc": "lockout_tagout='CLEARED' 且 ready_to_start=True，油温与压力正常",
                        "status": "已支持",
                        "evidence_ids": ["EVID-c4-status"]
                    },
                    {
                        "condition_id": "COND-RULE",
                        "logic_group": "OR",
                        "verification_type": "模型候选提案",
                        "desc": "日志未查询制冷站书面开机放行 SOP，仅能证明系统状态就绪，不代表覆盖全部制度规则",
                        "status": "缺适用规则",
                        "evidence_ids": []
                    }
                ],
                "evidences": [
                    {
                        "evidence_id": "EVID-c2-wo",
                        "run_id": "IND-002-r1",
                        "event_id": "c2",
                        "tool": "maintenance_workorders.get",
                        "json_path": "trace[1].result.{work_order_id, status, completed_at}",
                        "raw_snippet": "work_order_id: 'WO-28501', status: 'COMPLETED', completed_at: '2026-11-14T13:45:00+08:00'",
                        "scope_check": "设备 CH-02 匹配"
                    },
                    {
                        "evidence_id": "EVID-c3-sign",
                        "run_id": "IND-002-r1",
                        "event_id": "c3",
                        "tool": "maintenance_workorders.get_signoff",
                        "json_path": "trace[2].result.{technician_signoff, supervisor_signoff}",
                        "raw_snippet": "technician_signoff: true, supervisor_signoff: true",
                        "scope_check": "双人签字完整"
                    },
                    {
                        "evidence_id": "EVID-c4-status",
                        "run_id": "IND-002-r1",
                        "event_id": "c4",
                        "tool": "plant_monitor.get_chiller_status",
                        "json_path": "trace[3].result.{lockout_tagout, ready_to_start, oil_temp_c, refrigerant_pressure_kpa}",
                        "raw_snippet": "lockout_tagout: 'CLEARED', ready_to_start: true, oil_temp_c: 42, refrigerant_pressure_kpa: 680",
                        "scope_check": "实时状态正常"
                    }
                ],
                "remediation_plan": [
                    {
                        "plan_id": "ACT-01",
                        "action_type": "候选工具调用",
                        "missing_or_issue": "如需验证完整制度合规性，可补充检索冷水机组开机放行 SOP",
                        "affected_claims": ["CLM-03"],
                        "candidate_call": "knowledge_base.search(collection='制冷站设备操作规程', query={'equipment_model': 'YORK-YT-350', 'topic': '保养后开机放行条件'})",
                        "success_criteria": "确认除工单双签与 LOTO 解除外无额外前置审批"
                    }
                ],
                "scorecard": {
                    "rule_version": "score-v0.1-prototype",
                    "high_risk_alert": "",
                    "support_score": 0.90,
                    "coverage_score": 1.00,
                    "uncertainty_score": 0.85,
                    "scope_note": "图内证据完整支持“工单完成”与“系统显示可启动”，但标出“缺适用放行SOP”边界。",
                    "review_sequence": [
                        "1. 确认技术员与主管签字时间戳早于提问时间",
                        "2. 现场操作员执行开机前常规巡视"
                    ]
                },
                "raw_trace": [
                    {"id": "c2", "tool": "maintenance_workorders.get", "result": {"status": "COMPLETED"}},
                    {"id": "c3", "tool": "maintenance_workorders.get_signoff", "result": {"technician_signoff": True, "supervisor_signoff": True}},
                    {"id": "c4", "tool": "plant_monitor.get_chiller_status", "result": {"ready_to_start": True}}
                ]
            }
        }
    }
}

# ==========================================
# 4. Markdown 成绩单导出生成函数
# ==========================================
def generate_markdown_report(case_obj, mode_name, mode_data):
    sc = mode_data["scorecard"]
    lines = [
        "# 工业智能体动态证据图与置信度复核成绩单",
        f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**运行标识**: Case: `{case_obj['case_id']}` | Run: `{case_obj['run_id']}` | Graph: `{case_obj['graph_version']}` | Answer: `{case_obj['answer_version']}` | 视图: `{mode_name}`",
        "",
        "---",
        "## 一、 用户问题与待回答目标 (User Goals)",
        f"- **原始问题**: {case_obj['user_question']}",
        f"- **AI 最终回答**: {case_obj['ai_answer']}",
        "",
        "### 目标回应覆盖情况:"
    ]
    for g in mode_data["user_goals"]:
        lines.append(f"- **[{g['goal_id']}]** {g['target']} -> **{g['coverage']}** ({g['note']})")

    lines.extend(["", "## 二、 原子结论拆解与证据判定"])
    for c in mode_data["atomic_claims"]:
        lines.append(f"- **[{c['claim_id']}]** `{c['status']}` | {c['text']} (关联证据: `{c['target_evidence'] or '无'}`)")

    lines.extend([
        "",
        f"## 三、 置信度成绩单 (评分规则: {sc['rule_version']})",
        f"- **已断言结论证据支持度**: {sc['support_score']:.2f}",
        f"- **用户问题回应覆盖度**: {sc['coverage_score']:.2f}",
        f"- **不确定性表达准确性**: {sc['uncertainty_score']:.2f}",
        f"- **范围声明**: {sc['scope_note']}"
    ])
    if sc["high_risk_alert"]:
        lines.append(f"- **严重冲突告警**: {sc['high_risk_alert']}")

    lines.extend(["", "## 四、 自动补证与重算计划"])
    for act in mode_data["remediation_plan"]:
        lines.append(f"- **[{act['plan_id']}] ({act['action_type']})**: {act['missing_or_issue']} -> 建议动作: `{act['candidate_call']}`")

    lines.extend(["", "## 五、 原始轨迹证据定位"])
    for ev in mode_data["evidences"]:
        lines.append(f"- **[{ev['evidence_id']}]** (`{ev['run_id']}` / `{ev['event_id']}` / `{ev['tool']}`) 路径 `{ev['json_path']}`: `{ev['raw_snippet']}`")

    lines.extend([
        "",
        "---",
        "> **声明**：本报告为基于现有监控日志的离线证据审核结果，不代表真实物理世界的最终概率保证；图内完整不代表覆盖全部厂内制度。"
    ])
    return "\n".join(lines)

# ==========================================
# 5. 侧边栏：案例切换、视图切换与版本契约
# ==========================================
st.sidebar.markdown("### 🎛️ 证据图复核控制台")
case_names = list(STATIC_CASES.keys())

if "case_idx" not in st.session_state:
    st.session_state["case_idx"] = 0

selected_case_name = st.sidebar.selectbox(
    "选择监控日志案例：",
    case_names,
    index=st.session_state["case_idx"]
)
st.session_state["case_idx"] = case_names.index(selected_case_name)

nav_c1, nav_c2 = st.sidebar.columns(2)
if nav_c1.button("⬅️ 上一案例", use_container_width=True):
    st.session_state["case_idx"] = (st.session_state["case_idx"] - 1) % len(case_names)
    st.session_state["selected_evidence_id"] = "ALL"
    st.rerun()
if nav_c2.button("下一案例 ➡️", use_container_width=True):
    st.session_state["case_idx"] = (st.session_state["case_idx"] + 1) % len(case_names)
    st.session_state["selected_evidence_id"] = "ALL"
    st.rerun()

case_obj = STATIC_CASES[case_names[st.session_state["case_idx"]]]

# 状态隔离：切换案例时重置高亮筛选
if "active_case_id" not in st.session_state or st.session_state["active_case_id"] != case_obj["case_id"]:
    st.session_state["active_case_id"] = case_obj["case_id"]
    st.session_state["selected_evidence_id"] = "ALL"

available_modes = list(case_obj["modes"].keys())
selected_mode = st.sidebar.radio("🔄 视图切换 (需求 G6 补证前后对照)：", available_modes)
mode_data = case_obj["modes"][selected_mode]

if st.sidebar.button("🧹 重置筛选与会话状态", use_container_width=True):
    keep_idx = st.session_state["case_idx"]
    st.session_state.clear()
    st.session_state["case_idx"] = keep_idx
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='background:#ffffff; padding:12px 14px; border-radius:10px; font-size:0.83rem; border:1px solid #cbd5e1; box-shadow:0 1px 2px rgba(0,0,0,0.03);'>
<div style='font-weight:700; color:#0f172a; margin-bottom:6px;'>📋 运行与版本契约</div>
• <b>Case ID</b>: <code>{case_obj['case_id']}</code><br>
• <b>Run ID</b>: <code>{case_obj['run_id']}</code><br>
• <b>Graph Ver</b>: <code>{case_obj['graph_version']}</code><br>
• <b>Answer Ver</b>: <code>{case_obj['answer_version']}</code><br>
• <b>所属场景</b>: {case_obj['scene_tag']}
</div>
""", unsafe_allow_html=True)

# 版本一致性拦截
if not case_obj.get("version_consistent", True):
    st.error("🚨 版本一致性校验失败：Graph 与 Answer 版本不匹配，已阻断渲染。")
    st.stop()

# ==========================================
# 6. 顶部横幅与上下文卡片
# ==========================================
st.markdown(f"""
<div class="hero-banner">
    <div>
        <div class="hero-title">🔍 工业智能体动态证据图与置信度复核看板</div>
        <div class="hero-sub">双向问题/回答拆解 · AND/OR 路径逻辑推导 · 离线补证与重算计划 · 三维置信度成绩单</div>
    </div>
    <div class="hero-pill">当前视图：{selected_mode}</div>
</div>
""", unsafe_allow_html=True)

ctx_chips = "".join([
    f"<span class='ctx-chip'>🔹 <b>{k}</b>: <code>{v}</code></span>"
    for k, v in case_obj["visible_context"].items()
])

# 统计本案例结论分布速览
claims_list = mode_data["atomic_claims"]
cnt_sup = sum(1 for c in claims_list if c["status"] == "已支持")
cnt_con = sum(1 for c in claims_list if c["status"] == "与证据矛盾")
cnt_ins = sum(1 for c in claims_list if c["status"] not in ("已支持", "与证据矛盾"))

st.markdown(f"""
<div class="meta-box">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <span class='ctx-chip'>🆔 <b>Run</b>: <code>{case_obj['run_id']}</code></span>
            {ctx_chips}
        </div>
        <div style="display:flex; gap:8px; font-size:0.82rem; font-weight:600;">
            <span style="background:#dcfce7; color:#166534; padding:3px 9px; border-radius:6px;">🟢 支持: {cnt_sup}</span>
            <span style="background:#fee2e2; color:#991b1b; padding:3px 9px; border-radius:6px;">🔴 矛盾: {cnt_con}</span>
            <span style="background:#fef3c7; color:#92400e; padding:3px 9px; border-radius:6px;">🟡 待证/缺规: {cnt_ins}</span>
        </div>
    </div>
    <div class="question-banner">
        <span>🙋 用户提问：</span>
        <span style="color:#1e3a8a;">“{case_obj['user_question']}”</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7. 区域 1：双向拆解——用户待回答目标 & AI 原子结论 (浅蓝大框)
# ==========================================
with st.container(border=True):
    st.markdown('<div class="region-marker-1"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header">
        <div class="section-title">📌 区域 1｜双向拆解：待回答目标与原子结论评价</div>
        <span class="section-tag">需求 G1 · 双向构图</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("从“用户问题目标”与“AI 回答原子结论”两个方向同时展开；选择右侧下拉项可联动高亮下方对应证据原文。")

    st.markdown(f"""
    <div class="answer-box">
        <div style="font-size:0.82rem; font-weight:600; color:#2563eb; margin-bottom:4px;">🤖 智能体原始输出 (ai_answer)</div>
        <div style="font-size:0.97rem; color:#0f172a; line-height:1.6;">{case_obj['ai_answer']}</div>
    </div>
    """, unsafe_allow_html=True)

    g_col, c_col = st.columns([1, 1.45], gap="large")

    with g_col:
        st.markdown("**🎯 方向 A：用户待回答目标 (User Goals)**")
        for g in mode_data["user_goals"]:
            st.markdown(f"""
            <div class="goal-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:5px;">
                    <span style="font-weight:700; color:#0f172a; font-size:0.92rem;">[{g['goal_id']}] {g['target']}</span>
                    <span style="white-space:nowrap;">{render_badge(g['coverage'])}</span>
                </div>
                <div style="font-size:0.84rem; color:#475569; line-height:1.45;">{g['note']}</div>
            </div>
            """, unsafe_allow_html=True)

    with c_col:
        head_c1, head_c2 = st.columns([1.15, 1])
        with head_c1:
            st.markdown("**💬 方向 B：回答原子结论拆解 (Atomic Claims)**")
        with head_c2:
            claim_opts = ["全部证据 (展示完整轨迹)"] + [f"{c['claim_id']}: {c['text'][:14]}..." for c in mode_data["atomic_claims"]]
            current_idx = 0
            for idx_opt, opt_str in enumerate(claim_opts):
                if idx_opt > 0:
                    cid_opt = opt_str.split(":")[0]
                    for c_item in mode_data["atomic_claims"]:
                        if c_item["claim_id"] == cid_opt and c_item["target_evidence"] == st.session_state["selected_evidence_id"] and st.session_state["selected_evidence_id"] != "ALL":
                            current_idx = idx_opt
            chosen_filter = st.selectbox("聚焦结论联动证据：", claim_opts, index=current_idx, label_visibility="collapsed")
            if chosen_filter.startswith("全部证据"):
                st.session_state["selected_evidence_id"] = "ALL"
            else:
                cid = chosen_filter.split(":")[0]
                for c in mode_data["atomic_claims"]:
                    if c["claim_id"] == cid:
                        st.session_state["selected_evidence_id"] = c["target_evidence"]

        for c in mode_data["atomic_claims"]:
            is_hl = (c["target_evidence"] == st.session_state["selected_evidence_id"] and st.session_state["selected_evidence_id"] != "ALL")
            hl_style = "border:2px solid #2563eb; background:#eff6ff;" if is_hl else ""
            st.markdown(f"""
            <div class="claim-item" style="{hl_style}">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:6px;">
                    <div style="font-size:0.93rem; color:#0f172a; line-height:1.45;"><b>[{c['claim_id']}]</b> {c['text']}</div>
                    <div style="white-space:nowrap;">{render_badge(c['status'])}</div>
                </div>
                <div style="font-size:0.8rem; color:#64748b; display:flex; flex-wrap:wrap; gap:10px;">
                    <span>🎯 关联目标: <code>{c['linked_goal']}</code></span>
                    <span>📊 断言强度: <code>{c['assertion_strength']}</code></span>
                    <span>🔗 推导条件: <code>{c['condition_id']}</code></span>
                    <span>📎 证据: <code>{c['target_evidence'] or '缺失'}</code></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 8. 区域 2 (浅绿大框) & 区域 3 (浅紫大框) 并排展示
# ==========================================
col_r2, col_r3 = st.columns([1, 1], gap="medium")

with col_r2:
    with st.container(border=True):
        st.markdown('<div class="region-marker-2"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-header">
            <div class="section-title">🌳 区域 2｜证据结构与逻辑推导层</div>
            <span class="section-tag">需求 G3 / G4 / G5</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("区分 AND 必要条件与 OR 替代路径，标明“代码复算”与“模型提案”。")
        for cond in mode_data["conditions"]:
            st.markdown(f"""
            <div class="cond-card">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:7px;">
                    <div style="display:flex; align-items:center; flex-wrap:wrap; gap:5px;">
                        <b style="color:#0f172a; font-size:0.92rem;">{cond['condition_id']}</b>
                        {render_badge(cond['logic_group'])}
                        {render_badge(cond['verification_type'])}
                    </div>
                    <div>{render_badge(cond['status'])}</div>
                </div>
                <div style="font-size:0.89rem; color:#334155; line-height:1.5; margin-bottom:7px;">{cond['desc']}</div>
                <div style="font-size:0.8rem; color:#64748b;">
                    🔗 <b>支撑证据</b>: <code>{', '.join(cond['evidence_ids']) if cond['evidence_ids'] else '无有效支撑证据 (缺口)'}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)

with col_r3:
    with st.container(border=True):
        st.markdown('<div class="region-marker-3"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-header">
            <div class="section-title">📖 区域 3｜原始轨迹字段路径与证据原文</div>
            <span class="section-tag">需求 G2 · 可追溯溯源</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("严格定位到 run_id、事件 ID（如 c1）与原始 JSON 字段路径。")

        ev_list = mode_data["evidences"]
        active_ev = st.session_state["selected_evidence_id"]
        if active_ev != "ALL" and active_ev:
            matched = [e for e in ev_list if e["evidence_id"] == active_ev]
            if matched:
                st.info(f"🔍 已聚焦联动展示关联证据：`{active_ev}`（在区域 1 选“全部证据”可恢复全部）")
                ev_list = matched
            else:
                st.warning("⚠️ 当前选中的结论缺少对应证据支撑（属于证据缺口）。")

        for ev in ev_list:
            is_hl = (ev["evidence_id"] == active_ev and active_ev != "ALL")
            hl_cls = "evidence-highlight" if is_hl else ""
            st.markdown(f"""
            <div class="evidence-card {hl_cls}">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
                    <span style="font-weight:700; color:#0f172a; font-size:0.92rem;">📌 [{ev['evidence_id']}] 事件 <code>{ev['event_id']}</code> · <code>{ev['tool']}</code></span>
                    <span style="font-size:0.78rem; background:#f3e8ff; color:#6b21a8; padding:2px 7px; border-radius:4px; font-weight:600;">{ev['run_id']}</span>
                </div>
                <div style="font-size:0.81rem; color:#475569; line-height:1.5;">
                    • <b>JSON 路径</b>: <code>{ev['json_path']}</code><br>
                    • <b>范围/时效</b>: {ev['scope_check']}
                </div>
                <div class="snippet-box">{ev['raw_snippet']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 9. 区域 4：自动补证与重算计划 (浅暖黄大框)
# ==========================================
with st.container(border=True):
    st.markdown('<div class="region-marker-4"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header">
        <div class="section-title">🧭 区域 4｜自动补证与重算计划</div>
        <span class="section-tag">需求 B1 / B2 / B3</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("从未满足条件反推最小补查动作：区分“已有数据重算”、“生成候选工具调用参数”与“现场/人工确认”。")

    for act in mode_data["remediation_plan"]:
        st.markdown(f"""
        <div class="plan-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <b style="font-size:0.95rem; color:#0f172a;">[{act['plan_id']}]</b>
                    {render_badge(act['action_type'])}
                </div>
                <div style="font-size:0.82rem; color:#64748b;">受影响结论: <code>{', '.join(act['affected_claims'])}</code></div>
            </div>
            <div style="font-size:0.9rem; color:#334155; margin-bottom:4px;">
                <b>缺口与问题定位</b>：{act['missing_or_issue']}
            </div>
            <div class="call-box">▶ {act['candidate_call']}</div>
            <div style="font-size:0.83rem; color:#15803d; font-weight:500;">
                ✔ <b>预期判定成功条件</b>：{act['success_criteria']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 10. 区域 5：置信度成绩单 (浅珊瑚粉大框)
# ==========================================
with st.container(border=True):
    st.markdown('<div class="region-marker-5"></div>', unsafe_allow_html=True)
    sc = mode_data["scorecard"]
    st.markdown(f"""
    <div class="section-header">
        <div class="section-title">📊 区域 5｜置信度成绩单与高风险冲突标记</div>
        <span class="section-tag">规则版本: {sc['rule_version']}</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("分数仅代表基于现有日志的离线证据审核结果，在经过独立校准前不代表实际物理世界正确概率。")

    if sc["high_risk_alert"]:
        st.error(sc["high_risk_alert"])

    c_sup = "#16a34a" if sc["support_score"] >= 0.8 else ("#d97706" if sc["support_score"] >= 0.5 else "#dc2626")
    c_cov = "#16a34a" if sc["coverage_score"] >= 0.8 else ("#d97706" if sc["coverage_score"] >= 0.5 else "#dc2626")
    c_unc = "#16a34a" if sc["uncertainty_score"] >= 0.8 else ("#d97706" if sc["uncertainty_score"] >= 0.5 else "#dc2626")

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(render_score_card("① 证据支持度 (Support)", "已断言事实获适用证据支持的比例", sc["support_score"], c_sup), unsafe_allow_html=True)
    with m2:
        st.markdown(render_score_card("② 问题回应覆盖度 (Coverage)", "用户提问核心目标已回应或说明未知的比例", sc["coverage_score"], c_cov), unsafe_allow_html=True)
    with m3:
        st.markdown(render_score_card("③ 不确定性表达准确性", "措辞强度与证据匹配，未把预测/局部当确定", sc["uncertainty_score"], c_unc), unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#ffffff; border:1px solid #fecdd3; border-radius:8px; padding:10px 14px; font-size:0.87rem; color:#334155; margin-top:12px; margin-bottom:10px;">
        📌 <b>审核范围与局限声明</b>：{sc['scope_note']}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**🎯 建议人工复核顺序 (Review Sequence)**")
    for step in sc["review_sequence"]:
        st.markdown(f"<div class='review-step-card'>{step}</div>", unsafe_allow_html=True)

# ==========================================
# 11. 区域 6：三种方案同场景对比评测框架 (浅青碧大框)
# ==========================================
with st.container(border=True):
    st.markdown('<div class="region-marker-6"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header">
        <div class="section-title">📈 区域 6｜三种构图与验证方案对比评测框架</div>
        <span class="section-tag">需求第 6 节 · 60 条日志基准</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("比较纯代码规则、纯模型生成、模型提案+代码验证（混合主方案）在三项核心验收指标上的表现。")

    def load_experiment_metrics():
        curr = Path(__file__).resolve().parent
        for _ in range(3):
            fpath = curr / "experiment_metrics.json"
            if fpath.exists():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        return json.load(f), True
                except Exception:
                    pass
            curr = curr.parent
        return [
            {"method": "① 纯代码规则 (Rule-Only)", "false_support": "低 (受控字段内)", "gap_locate": "高 (规则覆盖内)", "insufficient_as_err": "中 (缺语义理解)", "note": "待读取实验 JSON 实测值"},
            {"method": "② 纯模型生成证据图 (LLM-Only)", "false_support": "较高 (易编造厂规)", "gap_locate": "中 (参数易幻觉)", "insufficient_as_err": "较高", "note": "待读取实验 JSON 实测值"},
            {"method": "③ 模型提案 + 代码验证 (推荐主方案)", "false_support": "最低 (代码强校验)", "gap_locate": "最高 (可复算+语义)", "insufficient_as_err": "最低 (保留未知态)", "note": "待读取实验 JSON 实测值"}
        ], False

    metrics_rows, is_real_exp = load_experiment_metrics()
    if not is_real_exp:
        st.info("ℹ️ 当前为静态评测框架占位表（未硬编码虚构百分比）。运行批量实验生成 `experiment_metrics.json` 后将自动填充实测数据。")

    rows_html = "".join([
        f"<tr style='border-bottom:1px solid #e2e8f0;'>"
        f"<td style='padding:10px 12px; font-weight:600; color:#0f172a;'>{r['method']}</td>"
        f"<td style='padding:10px 12px;'>{r['false_support']}</td>"
        f"<td style='padding:10px 12px;'>{r['gap_locate']}</td>"
        f"<td style='padding:10px 12px;'>{r['insufficient_as_err']}</td>"
        f"<td style='padding:10px 12px; font-size:0.82rem; color:#64748b;'>{r['note']}</td>"
        f"</tr>"
        for r in metrics_rows
    ])

    st.markdown(f"""
    <table style="width:100%; border-collapse:collapse; background:#ffffff; border:1px solid #99f6e4; border-radius:10px; overflow:hidden; font-size:0.86rem;">
        <thead>
            <tr style="background:#ccfbf1; border-bottom:2px solid #5eead4; text-align:left; color:#0f766e;">
                <th style="padding:10px 12px;">方案分组</th>
                <th style="padding:10px 12px;">错误结论被判为支持的比例 (越低越好)</th>
                <th style="padding:10px 12px;">缺口及补查参数定位准确率 (越高越好)</th>
                <th style="padding:10px 12px;">证据不足被误判为错误的比例 (越低越好)</th>
                <th style="padding:10px 12px;">数据状态</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

# ==========================================
# 12. 原始 Trace 展开与同版本导出
# ==========================================
with st.expander("🛠️ 查看底层原始工具轨迹 (trace JSON 审计)", expanded=False):
    st.json(mode_data["raw_trace"])

col_d1, col_d2 = st.columns(2, gap="medium")
md_report = generate_markdown_report(case_obj, selected_mode, mode_data)
col_d1.download_button(
    label="📄 导出同版本 Markdown 复核成绩单",
    data=md_report,
    file_name=f"Scorecard_{case_obj['run_id']}.md",
    mime="text/markdown",
    use_container_width=True
)

json_export = json.dumps({
    "case_id": case_obj["case_id"],
    "run_id": case_obj["run_id"],
    "graph_version": case_obj["graph_version"],
    "answer_version": case_obj["answer_version"],
    "mode": selected_mode,
    "analysis": mode_data
}, indent=2, ensure_ascii=False)

col_d2.download_button(
    label="💾 导出同版本结构化证据图 (.JSON)",
    data=json_export,
    file_name=f"EvidenceGraph_{case_obj['run_id']}.json",
    mime="application/json",
    use_container_width=True
)

st.markdown("""
<div style="background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:12px 16px; font-size:0.83rem; color:#92400e; margin-top:14px;">
    <b>⚠️ 证据审核边界声明</b>：<br>
    1. 本看板基于离线模拟监控日志（<code>trace</code>）进行事后证据图重建与复核，<b>分数仅代表现有日志内的证据审核结果，不代表物理世界实际正确概率</b>。<br>
    2. 图内证据完整不代表已覆盖所有未记录的厂内制度或现场真实状态；图形展示不代表原智能体生成回答时的隐藏思维过程。
</div>
""", unsafe_allow_html=True)
