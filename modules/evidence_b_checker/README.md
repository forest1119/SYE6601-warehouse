# 证据链 B：可交接原型

这是根据 A 组《6601问题(1).docx》文字回复实现的合成业务原型。可以本地运行，不需要 GPU、模型 API 或网络。已接入 Loop B 的 loop-b-mock 分支合同与维护模拟函数；该分支仍缺补偿条款和其他工具，尚未形成完整业务闭环。输入字段仍是待确认的交接格式。

## 零基础先做什么

最新版 notebook 请看第七阶段；前六阶段保留学习过程。这个文件夹主要给负责联调的同学。

1. 解压代码包，进入 checker_delivery 文件夹。
2. 使用 Python 3.10 或以上，运行 `python run_all.py --test`，同时生成中文说明并运行测试。
3. 打开 本次演示结果.md；详细结果在 examples 和 loop_b_results。
4. 运行 `python -m unittest -v` 检查回归测试。

核心代码只依赖标准库。vendor/confidence_a 是团队仓库评分模块的固定副本，不是B新写的评分算法。

## 同学如何调用

```python
from checker_api import check_payload, make_score_snapshot
result = check_payload({"task": task, "responses": responses, "rules": rules})
snapshot = make_score_snapshot(result, run_id="RUN-001", snapshot_id="SNAP-001")
```

Loop每次交入**全部最新材料的完整快照**，不只交新增一页。翻页合并由工具/Loop负责，只有查全时才声明 pagination_complete=true。Checker不调用工具、不计重试、不实际转人工。

也可以运行：

```sh
python run_checker.py examples/normal_input.json --output outputs/result.json --score-snapshot outputs/snapshot.json
```

正常退出码为0；输入错误为2。失败时输出文件写入INPUT_ERROR，避免保留上一次成功结论被误读。输入、结果、评分快照必须用不同路径。

## 文件作用

| 文件 | 用途 |
|---|---|
| checker_v2.py | 已加固的业务检查核心；保留旧名称便于已有测试导入 |
| checker_api.py | 给Loop的入口、评分格式转换、严格JSON读取 |
| run_checker.py | 命令行入口 |
| run_demo.py | 五个合成场景与评分示例 |
| test_checker_v2.py | 51项业务/输入边界自测 |
| test_handoff.py | 11项交接回归测试，包含前述51项及49个可评分业务快照 |
| rules.json | A原始规则副本，不是会后重新发布的规则版本 |
| INTERFACE.md | 各组交接字段和约定 |
| TEAM_TODO.md | 当前真正缺的外部资料 |

## 已验证什么

支持完整合同、VIP无适用合同回退、合同否决、维护交集与去重、净时长、根因核实、提前否决、UNKNOWN/CONFLICT、规则引用和查询回执追溯。所有开发自测不等于独立测试组验收，不报告模型准确率。

评分中的“证据充分性”不是答案正确概率。提前否决后，未查项仍保留在分母里，不通过删除它们把分数凑到100。评分策略和检查项编号仍是草案。

## 来源与版本

- 业务依据：用户提供的 rules.json、obligations.json、A组《6601问题(1).docx》文字回复。
- 评分副本：https://github.com/forest1119/SYE6601-warehouse
- 固定提交：14fae4f4a64be18f749939797b1906a009debbd0，modules/confidence_a_mvp/confidence_a。
- vendor/LICENSE 保留团队仓库许可证。评分代码原样复用。
- 本包没有向团队仓库推送任何修改。

## 新增：同学模拟工具联调
运行 `python run_loop_b_integration.py`，查看loop_b_results。该流程实际调用同学的模拟函数，不是复制结果。当前8个场景因缺关键业务数据，均返回UNDETERMINED。具体缺口和可直接发给同学的话见LOOP_B_NEXT.md。测试方法已扩展为22项，包含已有51项开发场景及新增模拟工具联调。

Loop B源码固定为d74ec4e7927dc92dd7e65adfb7bf430df59164a5；main评分源码仍为14fae4f4a64be18f749939797b1906a009debbd0。两个来源版本分别记录，不称为main已合并。
