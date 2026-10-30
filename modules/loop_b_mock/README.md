# Loop B 查询工具草稿

这是可独立运行、等待团队确认接口的阶段版本。只用Python标准库，不用安装额外依赖。

## 如何运行

解压整个文件夹。在CMD输入 python 和一个空格，把 run_demo.py 拖进去，按回车。
程序一次运行8个例子，将结果保存在程序旁边的 demo_results 文件夹。
不要只双击脚本，以免运行完窗口关闭。

## 文件说明

- mock_tools.py：合同与维护查询函数，供Loop A引用；引用时不会执行演示。
- data/contracts.json：两位虚构客户的合同元数据。
- data/maintenance.json：客户002的一条虚构维护记录。
- run_demo.py：独立演示与结果保存。
- demo_results：示例查询返回、调用记录及人工核查单。

## 调用方式

from mock_tools import get_customer_contract, list_maintenance
get_customer_contract("001")
get_customer_contract("002", scenario="forbidden")
list_maintenance("002")
list_maintenance("002", page_token="page_2")

scenario支持 normal、forbidden、timeout、old_version、conflicting_materials。
只有正常完整查询且records为空，才表示当前模拟数据集内没有该客户记录；是否可作为业务上的不存在证据由Checker核验。
403和超时保持pagination_complete=false，不伪装成完整空结果。
维护查询第一页故意为空但提供下一页标记；第二页返回按客户过滤的记录。

## 与搭档的边界

Loop A选择工具、控制轮数及停止，Checker判断证据有效性与四态。
build_escalation只整理Loop A提供的升级上下文，不自行决定升级。
演示中的task_id、轮数、升级理由是样例。费用单位是模拟值，elapsed_ms是本地实际测量值。
相反材料场景仅在statement里加入相反的占位描述，不代表Checker一定会判为CONFLICT；正式业务矛盾条款需规则组确认。
fetched_at与实际耗时每次变化，查询记录及状态在相同输入和数据下固定。

## 尚未完成

接口尚未与Loop A和Checker联调；状态名、字段及目录均为草案。
合同目前仅有元数据，不含可判断补偿的条款；维护记录也仅用于演示。
尚无政策、套餐、故障等其他工具，不筛选历史生效区间；旧版本故意原样交Checker核验。
日志目前由演示程序记录；正式任务参数和日志入口需共同确认。
不是完整Loop B交付，也不包含整个小组系统。

## 已验证

客户过滤；完整空结果；两页查询；403；模拟超时；旧版字段；相反材料占位；非法页标记；升级单生成；引用模块不自动写文件。
