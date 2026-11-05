"""命令行使用：python run_checker.py examples/normal_input.json --output outputs/normal.json"""
import argparse
import sys
from pathlib import Path
from checker_api import check_payload,make_score_snapshot,read_json,write_json
from checker_v2 import InputError

def main():
    parser=argparse.ArgumentParser(description='证据链B检查器（合成接口草案）')
    parser.add_argument('input');parser.add_argument('--output',required=True)
    parser.add_argument('--score-snapshot')
    parser.add_argument('--run-id',default='DEMO-RUN')
    parser.add_argument('--snapshot-id',default='DEMO-SNAPSHOT')
    args=parser.parse_args()
    paths=[Path(args.input).resolve(),Path(args.output).resolve()]
    if args.score_snapshot:paths.append(Path(args.score_snapshot).resolve())
    if len(paths)!=len(set(paths)):
        print('输入文件、输出文件和评分快照必须使用不同路径',file=sys.stderr)
        return 2
    try:
        result=check_payload(read_json(args.input))
        snapshot=make_score_snapshot(result,args.run_id,args.snapshot_id) if args.score_snapshot else None
        write_json(args.output,result)
        if snapshot is not None:write_json(args.score_snapshot,snapshot)
    except (InputError,TypeError,KeyError) as error:
        # 清除旧成功结果的含义，防止下游误读上一次的分数或结论。
        failure={'status':'INPUT_ERROR','message':str(error)}
        write_json(args.output,failure)
        if args.score_snapshot:write_json(args.score_snapshot,failure)
        print('输入或接口错误：'+str(error),file=sys.stderr)
        return 2
    print('当前结论：'+result['checker_decision'])
    print('已保存：'+args.output)
    return 0
if __name__=='__main__':raise SystemExit(main())
