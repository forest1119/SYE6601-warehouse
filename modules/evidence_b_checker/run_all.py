"""一键运行全部演示，生成中文结果。只组织执行，不修改判断规则。"""
import argparse
import subprocess
import sys
from pathlib import Path
from run_demo import run_demo
from run_loop_b_integration import run_integration

# 英文状态保留在JSON中；这里只增加给人看的中文说明。
LABELS = {'RECOMMEND_COMPENSATION': '建议补偿', 'DO_NOT_RECOMMEND': '不建议补偿',
          'UNDETERMINED': '暂时无法判断'}

def main():
    parser = argparse.ArgumentParser(description='运行证据链B演示并生成中文说明')
    parser.add_argument('--test', action='store_true', help='同时运行开发自测')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    # 两组样例分开放，不能把合成完整案例误当作同学工具已经返回的材料。
    full = run_demo()
    actual = run_integration()
    lines = ['# 本次演示结果', '', '这些是合成业务演示，不是真实客户补偿决定。',
             '', '## 一、完整合成材料的五种情况']
    for row in full:
        decision = row['decision']
        lines.append(f"- {row['case']}：{LABELS.get(decision, decision)}；缺口数 {row['gap_count']}。")
    lines += ['', '## 二、同学模拟工具的八种情况']
    for row in actual:
        codes = '、'.join(row['adapter_gaps']) or '适配层未新增字段缺口；仍需查看Checker的业务缺口'
        lines.append(f"- {row['case']}：{LABELS.get(row['decision'], row['decision'])}；{codes}。")
    lines += ['', '## 怎样看详细原因',
              'examples目录保存完整合成输入、Checker输出、评分快照和成绩单。',
              'loop_b_results目录保存同学工具的原始返回、字段转换和业务检查结果。',
              'UNKNOWN表示资料不足；REFUTE表示有效材料明确不满足某项要求。',
              '评分是证据充分性的演示分数，不是答案正确概率。',
              '工具查询成功不等于资料完整；适配成功不等于可以赔偿。',
              '自动决定补查哪个工具、最多三轮与实际转人工仍由Loop A负责。']
    if args.test:
        # 使用当前Python，避免电脑里多个Python造成环境混乱。
        completed = subprocess.run([sys.executable, '-m', 'unittest', '-v'], cwd=root)
        lines += ['', '开发自测：' + ('通过' if completed.returncode == 0 else '失败，请检查终端错误；不要宣称验收通过')]
        if completed.returncode:
            (root/'本次演示结果.md').write_text('\n'.join(lines), encoding='utf-8')
            return completed.returncode
    else:
        lines += ['', '这次没有运行测试；需要时执行 python run_all.py --test。']
    target = root/'本次演示结果.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    print('已生成中文结果：', target)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
