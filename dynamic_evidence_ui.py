"""Local review interface. Launch with streamlit run dynamic_evidence_ui.py."""

import json

import streamlit as st

from dynamic_evidence.cases import make_case
from dynamic_evidence.controller import Harness
from dynamic_evidence.evaluate import GOLD
from dynamic_evidence.mock_model import FixtureModel
from dynamic_evidence.models import OpenRouter
from dynamic_evidence.report import IDENTITY, markdown

st.set_page_config(page_title="故障补偿证据复核", layout="wide")
st.title("故障补偿证据复核")
st.caption("合成业务演示 · 证据与成绩单只覆盖已声明范围")
case = st.selectbox("案例", tuple(GOLD), key="case")
mode = st.radio("执行方式", ("模拟联调", "OpenRouter 实跑"), horizontal=True)
question = st.text_input("问题", "Is this outage eligible for compensation?")
candidate = st.text_area("候选回答（可留空）")
selection = (case, mode, question, candidate)
if st.session_state.get("selection") != selection:
    st.session_state.pop("bundle", None)
    st.session_state.selection = selection
buttons = st.columns(2)
if buttons[1].button("重置结果"):
    st.session_state.pop("bundle", None)
if buttons[0].button("开始核查"):
    st.session_state.pop("bundle", None)
    try:
        model = OpenRouter.from_env() if mode == "OpenRouter 实跑" else FixtureModel()
        task, tool = make_case(case, question, candidate or None)
        with st.spinner("取证、建链与校验中"):
            st.session_state.bundle = Harness(model, tool).run(task)
    except ValueError as error:
        st.error(str(error))
bundle = st.session_state.get("bundle")
if not bundle:
    st.stop()
graph, answer, card = (bundle[key] for key in ("graph", "answer", "scorecard"))
if not all(graph[k] == answer[k] == card[k] for k in IDENTITY):
    st.warning("图、答案与成绩单版本尚未对齐。")
    st.stop()
st.subheader(answer["text"])
st.write(f"{card['level']} · {graph['workflow_status']} · {bundle['mode']} · v{graph['graph_version']}")
st.caption(card["scope_declaration"])
for gap in card["review_priority"]:
    st.warning(f"{gap['gap_type']} · {gap['reason']}")
summary, structure, evidence, changes = st.tabs(("成绩单", "主张与依赖", "证据原文", "补证与版本"))
with summary:
    st.table([{"分项": key, "计数": f"{value[0]}/{value[1]}"} for key, value in card["parts"].items()])
    st.write(f"停止原因 {card['stop_reason']}")
    st.download_button("下载成绩单 Markdown", markdown(bundle), "scorecard.md", "text/markdown")
    st.download_button("下载完整 JSON", json.dumps(bundle, ensure_ascii=False, indent=2), "run.json", "application/json")
with structure:
    history = bundle["history"] or [graph]
    version = st.selectbox("查看图版本", [g["graph_version"] for g in history],
                           index=len(history)-1, key=graph["run_id"])
    snapshot = next(g for g in history if g["graph_version"] == version)
    claims = {n["id"]: n.get("text", n["id"]) for n in snapshot["nodes"] if n["type"] == "claim"}
    if claims:
        claim = st.selectbox("展开主张", list(claims), format_func=claims.get,
                             key=f"claim-{graph['run_id']}-{version}")
        related = {claim}
        while True:
            expanded = related | {e["to"] for e in snapshot["edges"] if e["from"] in related}
            expanded |= {e["from"] for e in snapshot["edges"]
                         if e["to"] in related and e["type"] in ("supports", "refutes")}
            if expanded == related:
                break
            related = expanded
        st.dataframe([n for n in snapshot["nodes"] if n["id"] in related])
        st.dataframe([e for e in snapshot["edges"] if {e["from"], e["to"]} <= related])
    else:
        st.info("此版本没有已发布的主张节点。")
    with st.expander("语义审核"):
        st.json(snapshot["checks"])
with evidence:
    for item in card["evidence"]:
        with st.expander(f"{item['source_id']} · {item['locator']}"):
            st.write(item["excerpt"])
            st.write(f"记录 {item['record_id']} · 调用 {item['call_id']}")
            node = next(n for n in graph["nodes"] if n["id"] == f"evidence:{item['record_id']}")
            st.json(node["metadata"])
with changes:
    for item in bundle["history"]:
        with st.expander(f"图版本 {item['graph_version']} · {len(item['changes'])} 项变化"):
            st.json(item["changes"])
    st.json(bundle["action_log"])
