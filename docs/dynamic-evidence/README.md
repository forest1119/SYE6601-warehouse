# 动态证据链与复核 Demo

新版原型实现合成故障补偿的自动建链、增量审核、定向补证、置信度成绩单及复核页面。主场景 DYN-01 先按通用时长政策建图，随后查到专属合同，从原句发现工单时限，再查询工单并重新判断。完整轨迹保存每版图、工具回执、模型输入输出和最终成绩单。

## 运行

Python 3.10+。后端与单元测试只用标准库。以下命令从仓库根目录运行。

```powershell
python -m unittest discover -s tests -p test_dynamic_evidence.py -v
python -m dynamic_evidence --case DYN-01
python -m dynamic_evidence --suite
python -m dynamic_evidence --replay docs/dynamic-evidence/records/dyn01-model-replay.json
python -m dynamic_evidence.unified
python -m dynamic_evidence.unified --ticket-forbidden
```

模拟运行标为 `simulated`，缓存重放标为 `replay`。实时运行从进程环境读取 `OPENROUTER_API_KEY`，无需把密钥填入文档。真实 API 推理使用合成业务数据，工具仍是合成环境。

```powershell
python -m dynamic_evidence --mode live --case DYN-01 --repeat 3
python -m dynamic_evidence --mode live --case DYN-01 --strategy fixed
python -m dynamic_evidence --mode live --case DYN-01 --strategy prompt
```

默认建链模型为 `qwen/qwen3.8-27b`，语义复核为 `qwen/qwen3.6-35b-a3b`。可通过 `BUILD_MODEL`、`REVIEW_MODEL` 覆盖。每次运行记录原始模型输出、请求阶段、模型、用量与成本。默认最多 3 轮补证、10 次工具调用、10 次模型调用、8 次发布图、100 个节点、150 秒调度预算及 0.10 美元模型用量预算。远端单次请求最多等待 45 秒，费用按回执事后核算，超限后立即停止。工具适配器承担外部 I/O 自身超时。

```powershell
python -m pip install -r requirements-review.txt
python -m streamlit run dynamic_evidence_ui.py
```

页面有模拟和实时模式、案例选择、可选候选回答、主张与证据定位、版本回放、导出。切换输入和重置会清除当前结果。普通使用者先看结果、关键缺口和原文，详细轨迹可展开。

## 分工与替换位置

| 分工 | 目前入口 | 队友接入时主要改哪里 |
|---|---|---|
| 01 建链 | `graph.build_candidate_graph(task, records, previous_graph, latest_answer, call_model)` | 实现同签名，或在注入函数中映射字段。模型只看问题、候选回答及已取回原文 |
| 02 校验 | `graph.review_graph(task, previous_graph, proposal, tool_receipts, call_model, cache)` | 替换 `Harness(reviewer=...)`，保留独立必查、语义审核、四态和版本合同 |
| 03 调度 | `controller.Harness.run(task, strategy=...)` | 工具预算与停止集中在 `Budget` 和 controller |
| 04 工具 | `tools.LoopBAdapter(query, extensions)` | 已对齐 `loop-b-mock` 草稿的 `query(source_type, customer_id, scenario=..., page_token=...)`，分支合并后可直接导入。政策、故障、工单经 extensions 提供 |
| 05 案例与真值 | `cases.make_case`、`matrix.MATRIX`、`evaluate.GOLD` | 运行材料和评测标注分开，按团队确认规则替换数据和标签 |
| 06 实验 | `python -m dynamic_evidence` 与 `evaluate.assess/summarize` | 新对照走 strategy，实际输出保留在运行 JSON |
| 07 成绩单 | `report.scorecard(graph, answer, action_log)` | 读取覆盖、四态、阻断及版本，等级与指标在此修改 |
| 08 复核 | `dynamic_evidence_ui.py` | 页面只读同版本 bundle，复核视图和下载可独立替换 |

示例接口边界：

```python
from dynamic_evidence.controller import Harness
from dynamic_evidence.tools import LoopBAdapter

provider = LoopBAdapter(team_query, extensions=extension_query)
bundle = Harness(model, provider, builder=team_build, reviewer=team_review).run(task)
```

上述 team 函数需由调用方提供。常规入口保留原合成数据以重放历史结果。`dynamic_evidence.unified` 直接调用团队主分支的 `loop_b_unified`，保留工具原调用编号、结构化原文定位及人工复核包。见 [集成与开会交接](integration.md)。

详细约定见 [接口草案](contracts.md)，评估口径和试验记录见 [测试记录](validation.md)。人类复核对照说明见 [复核方案](review-study.md)。

## 当前业务范围

预先声明基础必查来源、专属合同覆盖通用规则、合成维护排除，以及时长与工单期限两类可执行原子条件。具体阈值和新增工单依赖从取回条款抽取。复杂转引、自由文本额外承诺、范围不明和语义未决进入复核。代码核对原句、适用性、单位、完整查询与受限比较。语义复核由单独请求完成，仍可能与建链共享错误。

成绩单按已声明范围展示等级和分项。有效反驳也算完成，关键缺口同时阻断肯定与否定。采用无总分的新版显示，旧版 49 分上限只属于旧模块。合成场景中的规则效力和来源优先关系由本原型显式配置，最终口径由团队签认。
