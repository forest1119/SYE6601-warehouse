import json
import pandas as pd
import os


def analyze():
    # 1. 读取原始结果文件
    result_path = os.path.join(os.getcwd(), 'experiment_results.json')
    if not os.path.exists(result_path):
        print("❌ 找不到 experiment_results.json，请先运行 pytest！")
        return

    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    print("=" * 60)
    print("📊 实验结果统计报告 (已同时保存为本地文件)")
    print("=" * 60)

    # 2. 打印到终端
    print("\n【1. 准确率对比】")
    accuracy = df.groupby('method')['is_correct'].mean()
    print(accuracy.to_markdown())

    print("\n【2. 资源消耗对比 (平均值)】")
    cost_metrics = df.groupby('method')[['queries', 'cost']].mean()
    print(cost_metrics.round(3).to_markdown())

    print("\n【3. 失败案例归因分析】")
    failures = df[df['is_correct'] == False]
    if not failures.empty:
        for _, row in failures.iterrows():
            print(f"- 案例 {row['task_id']} | 方法: {row['method']}")
            print(f"  期望: {row['expected_status']} / {row['expected_decision']}")
            print(f"  实际: {row['actual_status']} / {row['actual_decision']}")
    else:
        print("✅ 所有方法在所有案例上均表现正确（基于当前模拟数据）。")

    # 3. 【新增功能】自动保存为 CSV 文件，方便用 Excel 打开
    csv_path = os.path.join(os.getcwd(), 'experiment_report.csv')
    # 使用 utf-8-sig 编码，防止 Excel 打开时中文乱码
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 详细数据已自动保存到本地文件: {csv_path}")
    print("   (你可以直接在文件夹里双击它，用 Excel 打开查看！)")


if __name__ == "__main__":
    analyze()