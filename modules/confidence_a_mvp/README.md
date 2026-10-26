# 07A 独立评分与指标最小模块

本模块接收 Checker 已经完成的证据判断，输出可解释的证据评分卡；另一个入口从每次运行的独立评审记录计算指标。它不决定是否赔偿、不选择工具，也不接大模型。

这是独立新工作区，不依赖旧 `07A_评分与指标_工作区`，不修改 01A 文件。接口为 `0.1-draft`，团队尚未确认。业务待办在 [待团队确认](docs/03_待团队确认.md)。

## 先运行

需要 Python 3.10 或以上，运行和测试均只用标准库，无须安装依赖。在本文件所在目录打开终端：

```powershell
python tools/run_demo.py
```

这条命令先运行全部测试，通过后写出 `outputs/` 中的三个评分卡与演示指标。样例和原始文件保持不变。任一步测试失败就停止。

也可以分别运行：

```powershell
python -m unittest discover -s tests -v
python -m confidence_a score examples/03_contract_unknown.snapshot.json --policy policy.demo.json --output outputs/contract_unknown.json
python -m confidence_a metrics examples/runs.demo.json --output outputs/metrics.json
```

命令正常返回 0，输入错误返回 2，不生成新的评分文件。调用方应检查退出码；失败时不可显示上一次成功运行留下的旧文件。

## 三个可以直接讲解的样例

| 样例 | Checker 结论 | 已查明义务 | 原始分 | 展示分 | 可以展示确定结论 |
|---|---|---|---|---|---|
| [01 正常补偿](examples/01_supported.snapshot.json) | 建议补偿 | 5/5 | 100 | 100 | 是 |
| [02 证据充分但不补偿](examples/02_refuted.snapshot.json) | 不建议补偿 | 5/5，合同命题为 REFUTE | 100 | 100 | 是 |
| [03 关键合同未查](examples/03_contract_unknown.snapshot.json) | 尚未确定 | 4/5 | 80 | 49 | 否 |

每个输入旁边都有同名 `.scorecard.json`，08B 可直接读取。五条义务、来源名和合成引用是专门手写的接口演示，不是自动从 01A 推导出的规则。100 分只表示输入中已建模义务查明，不是正确概率或不存在未知政策的保证。

49 分是待确认的展示上限。硬门槛由 `gate_passed` 与 `may_present_definitive_decision` 控制，绝不能用 `score >= 某值` 代替。即使改变展示上限，也不会放行关键缺口。

## 交给同伴的最小接口

```python
from confidence_a import score_snapshot, evaluate_runs, ContractError

try:
    card = score_snapshot(checker_snapshot)
except ContractError as error:
    # 展示“输入不完整/不一致”，不要显示上一次评分。
    show_contract_error(str(error))
else:
    show_scorecard(card)

report = evaluate_runs(run_payload)
```

上面 `show_*` 是界面组自己的函数。复制 `confidence_a/` 到团队项目可导入的位置即可；若团队采用包管理，也可从本目录执行 `python -m pip install -e .`（这一步不是运行样例的必要条件）。

- 02B/03A：看 [接口草案](docs/01_接口草案.md)，提供评分输入的精简投影。
- 08B：直接读三份 scorecard；优先显示结论、阻断原因，再显示分数。
- 05A/06B：看 [指标口径](docs/02_指标口径.md)，支持性评审必须针对每次运行的真实证据。
- 01A/产品经理：看 [待团队确认](docs/03_待团队确认.md)。不需要为了本模块重命名所有现有字段。
- 开会时：可使用 [联调清单](docs/04_联调与群消息.md)。

## 实现范围

已实现严格输入校验、引用一致性校验、等权评分、硬门槛、分项解释、风险标签、独立运行指标、JSON Schema、三个样例和自动测试。

尚未完成团队真实接口联调、业务规则签认、真实模型基线或正式实验。演示指标来自手写数据，不能写成项目成绩。没有实现自动业务规则翻译、按来源等级替代证据、抓取日期衰减、模型裁判、复杂权重或校准概率。

## 目录

```text
confidence_a/     评分、契约、指标、命令入口
docs/            评分说明、接口、指标、待确认事项、联调清单
examples/        三组输入输出及独立评估演示
schemas/         与程序同源的 JSON Schema
tests/           语义边界、数据错误、命令行与导出一致性测试
tools/           一键演示、显式重新生成样例
policy.demo.json 可编辑的演示评分参数
outputs/         本地运行产物，不纳入 Git
```

接口以 `confidence_a/contracts.py` 为可执行草案源。修改契约后用 `python tools/make_examples.py` 显式重新生成演示输入输出与 schema，再运行测试；该命令只覆盖本新工作区的演示文件。修改样例业务含义时先修改生成器，防止之后重生成丢失。
