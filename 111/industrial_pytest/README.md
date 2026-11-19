# 工业模拟日志 pytest 交付包

适用 Python 3.10+。已包含本次用户确认的60条数据原始副本（data/industrial_logs.json），未修改案例内容。

## 直接运行

将整个 industrial_pytest 文件夹复制到现有项目根目录，例如 compensation_demo/industrial_pytest。在PyCharm终端切换到该文件夹：

```powershell
cd industrial_pytest
python -m pip install -r requirements.txt
python -m pytest -q
```

默认离线执行：61项检查（1项总量/编号检查 + 60条结构检查）；另有60条接口测试显示SKIPPED，因为还没有配置真实接口。这不是报错，也不表示接口测试通过。

只查看离线测试：

```powershell
python -m pytest -q -m "not interface"
```

如果放在其他位置，请切换到含pytest.ini的目录运行。不会改动已有项目配置。若从项目根目录运行且已有conftest.py，优先在本目录运行以减少配置冲突。

## 检查内容及界限

检查60条数量、连续唯一编号、六个顶层字段、字段类型、提问时间时区、工具事件/进度说明字段、c/s编号与工具类型。不会要求所有案例具有相同调用次数。

保留样本中有意设计的错误回答，不把ai_answer当成参考正确答案，不自动修正业务内容。

这些检查不验证保险/工业业务规则、语义正确性或说明文档，不代表数据已通过全部质量审核。

## 交给后续接口开发者

本包采用单案例适配函数，pytest会对每条案例分别调用一次，共60次。不是假定服务器有一个接受60条数组的HTTP批量接口。若团队只有服务端批量协议，应另行适配，不能直接套用本示例。

先确认团队接口：地址、认证、请求体、响应体、通过标准。这里没有凭空设置真实接口。

推荐在 adapter_http.py 修改两个函数：
- build_payload(case)：把一条完整日志映射为团队约定的请求体。
- normalize_response(raw)：把实际返回转换为本测试包的内部契约：

```python
{
    "prediction": {"这里放实际接口的判定字段": "实际值"},
    "raw_response": raw
}
```

prediction字段由项目组约定，不是本包推定的服务器协议。适配函数必须同步返回可JSON序列化的dict；如有异步接口，需在适配层桥接。也可以新建模块，不用HTTP示例：

```python
def evaluate(case):
    raw = your_existing_evaluator(case)
    return {"prediction": raw["实际判定对象"], "raw_response": raw}
```

接口应评估日志中智能体回答的质量；输入包含trace和ai_answer。不把配套案例说明、标签或参考结论发送给被测接口。

## 启用真实接口测试

确认并修改adapter_http.py的请求/响应映射之后，在PowerShell配置：

```powershell
$env:TRACE_EVAL_URL="替换为组里实际的完整接口地址"
$env:TRACE_EVAL_TOKEN="如需Bearer认证，在此填入；不需要则不设置"
python -m pytest -q -m interface --run-interface --adapter adapter_http:evaluate
```

密钥只放本机环境变量，不写入代码，不提供Qwen密钥；这是后续评测接口，不是数据生成接口。如果认证不是Bearer，修改适配器。

未提供预期结果时，只检查适配器成功返回非空prediction对象，不计算模型准确率，不保证业务结果正确。无自动请求重试，避免重复付费；默认串行执行，每条HTTP请求超时120秒，可用TRACE_EVAL_TIMEOUT环境变量调整。

每条调用结果保存到results/，包括run_id、数据集哈希、调用耗时、适配器返回和是否通过。失败记录包含异常类型。原始返回可能包含服务端信息，分享前检查；不记录认证头。每次文件带时间戳，不覆盖旧结果。需要对外分享数据时按项目约定处理。

## 可选：人工确认预期结果后对比

当前数据没有机器可读且经人工确认的标准标签。本包不按编号臆造标签。

创建独立expected.json，使用run_id映射到团队约定的prediction字段预期值；必须完整覆盖当前数据全部60个run_id，不允许漏项。形式如下（仅说明形式，不是实际标签）：

```text
{
  "某条完整run_id": {"接口判定字段": "人工确认的值"},
  ...完整列出所有60条...
}
```

示意中的省略号不是合法JSON，实际文件不能保留。请按团队实际字段制定，人工复核后再用。预期结果不混入主日志。

```powershell
python -m pytest -q -m interface --run-interface --adapter adapter_http:evaluate --expected expected.json
```

此时逐条精确比较预期文件列出的prediction顶层字段与值（含类型）；不对自由文本做逐字语义判分。缺字段、错值、类型不符均失败。需要证据位置匹配、容错或模型判分时，再按团队标准扩展check_prediction。

## 换数据与导出报告

```powershell
python -m pytest -q --dataset "你的数据集路径.json" --expected-count 60
python -m pytest -q --junitxml=pytest_report.xml
```

当前校验器限定IND编号和-r1运行；保险或同题多次运行需相应调整校验规则。

实际验证记录：
- 本次60条原始数据：61 passed，60 skipped（接口未开启）。
- 临时模拟适配器：60 passed，证明批量调度可用，不是实际模型效果。
- 预期比较的正确匹配与错误匹配路径已检查。
- 尚未调用组内真实接口，尚未建立人工确认的语义预期标签。
