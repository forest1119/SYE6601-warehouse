# Loop B 唯一新版交接

**新代码统一使用 modules/loop_b_unified。旧 modules/loop_b_mock 是待清理历史版本。**
**工单统一调用 PR #5 原版实现；本目录没有私有 get_ticket 工单实现。**

## 本岗位做什么

原始合成材料、可定位引用、查询范围与版本信息、分页/错误回执、任务与运行编号、调用日志，以及按Loop A提供的终止快照整理人工复核包。
不建图、不判断四态、不判断补偿、不控制重试或停止，不调用付费模型。

## 先运行

完整解压“LoopB_唯一新版交接包.zip”，在PyCharm打开 modules/loop_b_unified 整个文件夹。
右键 run_raw_demo.py → Run。结果保存到 raw_outputs/本次编号/。
右键 test_raw_evidence.py → Run：31项新版开发检查。
只用Python标准库，不用装依赖或配置API密钥。

## 文件分工

| 文件/目录 | 用途 |
| --- | --- |
| provider_setup.py | 唯一推荐查询入口，创建一次运行使用的provider |
| raw_evidence.py | 原文查询、定位、范围、分页、回执与日志 |
| review_handoff.py | 按Loop A终止快照整理复核包 |
| run_raw_demo.py | 给组员看的演示入口 |
| test_raw_evidence.py | 31项开发检查 |
| runtime_data/ | 四类本地来源原文和记录，不含标准图或答案 |
| vendor/pr5_dynamic/ | PR5未修改的固定源码及许可证，工单从这里取得 |
| tool_registry.json | 五个注册来源与参数约定 |
| examples/raw/ | 实跑返回、复核包和验证摘要 |
| dev_checks/ | 开发场景来源说明，不提供给模型 |
| UNIFIED_HANDOFF.md | 完整接口、数据来源、限制 |
| run_raw_integration.py | 可选，接PR5全框架的模拟验证，需 --team-root 参数 |

## Loop A怎样调用

```python
from provider_setup import create_provider

tools = create_provider(log_path="outputs/calls.jsonl")
task = {
    "task_id": "TASK-001", "run_id": "RUN-001",
    "customer_id": "C-DEMO", "incident_id": "I-DEMO",
    "event_time": "2026-10-01T00:00:00Z"
}
receipt = tools("CRM_CONTRACT_DB", task)
```

需要下一页时由Loop A传回next_page_token。需要工单时，仍用同一tools调用TICKET_DB，只会转接PR5。不要把整个测试配置、所有材料或开发场景路由拼给建链模型。

每个运行建议创建一个provider。集成项目需要将本模块目录放到Python可导入路径，避免同时加载旧目录的同名入口。已有PR5票据provider可通过pr5_ticket_provider参数注入，内置固定源码仅保证独立演示可运行。

## 已验证与未解决

31项开发检查通过，独立演示成功。另运行PR5模拟接入13例，12例输出一致，1例维护字段语义待确认。这里不是独立业务验收或真实模型成绩。

维护待确认：PR5审核代码读excluded，本版原始资料提供planned。计划维护不直接等于本次事故免责，不能由工具自动赋值。当前该例安全保留undetermined。
服务范围和转引上下文尚无补充业务签认；工具明确标明范围限制，不补造材料。

工具日志包含task_id/run_id/call_id/provider_call_id，PR5控制器若重命名顶层call_id，需要保留与provider_call_id的映射。升级包由Loop A显式调用，不按日志条数推算补查轮数。

## 上传和旧版清理

只用这一个包。GitHub选loop-b-mock分支，停在仓库首页，Add file → Upload files，拖入解压后的整个modules文件夹。
检查路径：modules/loop_b_unified/provider_setup.py。
提交标题：Replace Loop B handoff with unified raw-evidence module

确认新版文件上传成功后，可以在同一分支整体删除 modules/loop_b_mock，不要逐个删旧py文件。
删除前通知Loop A：后续改用新目录与上面的入口。旧目录的历史内容仍可从Git提交历史恢复。
其他组目录、根README、.github和PR5代码均不删除。

这次上传只会新增新版文件，网页上传不会自动删除旧目录。旧目录清理需要单独执行一次删除提交，详见MIGRATION.md。
