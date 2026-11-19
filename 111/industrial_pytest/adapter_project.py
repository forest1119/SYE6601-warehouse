"""
证据链组Python工程的适配入口。

拿到实际工程后，在这里导入并调用对方的函数。
目前明确留空，避免把模拟输出当成真实实验。
"""


def evaluate(case, context):
    """
    case：
        一条完整日志，包含问题、上下文、trace和ai_answer。

    context：
        数据版本等运行信息，不包含标准答案或案例说明。

    接入后的返回结构：

    {
        "prediction": {
            # 对方实际返回的判断字段
        },
        "raw_response": {
            # 对方完整原始结果
        },
        "graph_bundle": {
            # 映射成graph_checks.py要求的结构
        }
    }
    """

    raise NotImplementedError(
        "尚未接入证据链工程。"
        "请先取得Python调用函数、真实输入输出样例和图结构说明，"
        "再实现本函数；不要补造缺失的快照或模型调用。"
    )