# 人工复核对照方案

使用同一冻结答案快照构造三种材料。A 仅展示答案，B 加原始来源，C 加同版本成绩单。按参与者随机分配互不重复、难度相近的案例，轮换三个条件的顺序，避免同一人连续复核同一个案例。

每次记录匿名参与者编号、快照版本、展示条件、任务顺序、完成用时、是否判断正确建议、是否定位决定性来源、是否发现关键缺口、是否识别新增条件、下一步建议是否合理。正确性由预先冻结的答案表核对。原始记录和统计分开，按条件报告人数、完成次数、正确次数、用时中位数及异常。可参考字段：

```text
participant_id,case_id,run_id,graph_version,answer_version,condition,order,elapsed_seconds,decision_correct,source_correct,gap_correct,new_dependency_correct,next_step_correct
```

本次仅执行程序化页面烟测和本地自审。真实复核参与者与计时数据尚未收集，当前无法评价人工复核提效。
