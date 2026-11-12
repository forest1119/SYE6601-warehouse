# Loop B 工单查询交付

## 已实现什么

新增get_ticket：按customer_id和incident_id一起查询工单，返回原始submitted_at。
保留原合同、维护查询及数据，未修改补偿规则、Checker或Loop停止策略。
工单资料来自团队PR #5的合成案例，不是真实客户工单；来源记录在data/tickets.json。
固定来源提交：8d544b865e19c5bd286e14201af777efb694b81d。
来源文件：https://github.com/forest1119/SYE6601-warehouse/blob/8d544b865e19c5bd286e14201af777efb694b81d/dynamic_evidence/cases.py

## PyCharm运行

完整解压，用PyCharm打开包含run_ticket_demo.py的整个文件夹。
右键run_ticket_demo.py → Run。一次执行11次查询，结果和日志保存在ticket_results/本次时间目录。
右键test_ticket_tools.py → Run：18项工单检查。
右键test_handoff.py → Run：原12项日志升级检查。
总计30项开发检查通过。测试不需要安装第三方包。

## 最小调用

```python
from ticket_tools import get_ticket
response = get_ticket("C-DEMO", "I-DEMO")
```

数据沿用PR5的C-DEMO/I-DEMO，不把旧合同客户001/002伪装成同一个对象。
旧客户编号没有对应工单时，将返回本合成数据集中的完整空列表。
如需和旧合同一起跑全链路，需要团队确认一套共同的客户/事故样例，不能凭编号猜测关联。

支持的scenario：
- normal：submitted_at=2026-10-01T12:00:00Z。
- forbidden：FORBIDDEN、403，查询未完成。
- timeout：TIMEOUT，查询未完成；是确定性模拟，不会真的等待超时。
- missing_ticket：完整查询无记录。
- late_ticket：返回PR5的2026-10-02T00:00:01Z时间。
- boundary：返回PR5的2026-10-02T00:00:00Z时间。
- old_version：取回过期记录，仍是SUCCESS；是否适用交审核层。
- paged：第一页为空并返回page_2；显式传page_token="page_2"后返回记录并结束。

不会直接输出“逾期”“应赔”“不赔”。scenario名称只是测试场景，期限条件及起算点由规则/审核/控制层决定。
submitted_at是提交时间；fetched_at是本次取回时间；二者不能互换。
无权限、超时和坏数据绝不会以完整空列表冒充不存在。工具返回的完整性只针对当前合成文件内该客户和事故的查询。

## 带日志调用（Loop A）

```python
from loop_b_handoff import call_with_log
called = call_with_log(
    task_id="TASK-TICKET-001",
    tool_name="get_ticket",
    parameters={"customer_id": "C-DEMO", "incident_id": "I-DEMO"},
    log_path="outputs/ticket_calls.jsonl",
)
response = called["response"]
entry = called["log_entry"]
```

本次唯一修改的已有文件是loop_b_handoff.py：导入并注册get_ticket，其他行为保持。
工单直接返回含cost_units=1；日志含simulated_cost_units=1，是同一调用的两处描述，统计时选一种，不能相加。
没有自动重试、自动翻页或自动转人工；原升级单仍由Loop A显式请求。

## 接PR #5的扩展入口

```python
from dynamic_evidence.tools import LoopBAdapter
from mock_tools import query
from ticket_tools import extension_query
provider = LoopBAdapter(query, extensions=extension_query)
```

上面的组合仅覆盖合同、维护和工单。POLICY_DB、INCIDENT_DB不由本扩展提供，会明确报错。
如果团队已有政策和故障provider，在extensions中按source分派：TICKET_DB使用extension_query，其他来源继续调用原provider。
不要直接替换掉团队所有来源导致政策/故障无法查询。
要记录工单日志，可用上面的call_with_log执行工单分支。

## 实际接入验证（非真实模型实验）

run_ticket_integration.py --team-root <PR5仓库根目录>
需自行准备PR5固定提交的检出目录；完整运行包不捆绑团队动态框架源码。
在PyCharm的Run配置Parameters填写 --team-root 和路径即可；不需要使用记事本。
本次本地已运行PR5的真实LoopBAdapter、Harness和FixtureModel，只替换工单查询，其他来源继续使用PR5合成资料。
6种场景与原合成provider结果相同：
- DYN-01 normal：eligible。
- LATE-TICKET：ineligible。
- BOUNDARY：eligible。
- MISSING-TICKET：ineligible。
- TICKET-403：undetermined。
- DYN-01 paged：eligible。
这些是框架在其合成规则下的模拟输出，不是Loop B自行裁决，也不是业务口径的独立确认。
实际返回和接入报告在examples/ticket/，完整运行时轨迹另保存在本地ticket_results。

## 上传GitHub

上传“工单GitHub增量包”解压后的modules文件夹到loop-b-mock分支的仓库首页。
不要进入modules再拖整个modules，否则重复套目录。
上传列表应为modules/loop_b_mock/ticket_tools.py等。
包含7个新文件/数据/说明、实跑样例及1个已有文件更新（loop_b_handoff.py）。
同一分支提交会更新仍开放的PR #6；不需要改main或另开平行分支。
不要上传.idea、__pycache__和整批本地ticket_results目录。
提交标题：Add Loop B ticket submission query and integration examples

## 目前真正需要组员确认的内容

1. PR5已实现的合成工单由谁长期维护，是否采用本次Loop B实现。
2. 最终客户/事故样例编号；C-DEMO/I-DEMO与001/002如何统一。
3. 工单期限从哪个事件起算、是否含边界，由规则和审核负责人确认；Loop B只提供原时间。
4. 实际Loop A如何接日志与source路由，及主分支何时合并。

无需等待这些确认即可查询当前合成工单并给出实跑样例；不能据此承诺完整团队系统已联调通过。
