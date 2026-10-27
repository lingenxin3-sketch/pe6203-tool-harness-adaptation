"""Calibrate a local judge on development evidence, never formal test outcomes."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tool_adapt.llm import LocalModel
from tool_adapt.official import OfficialEvaluator
from tool_adapt.experiment import save

ROOT=Path(__file__).resolve().parents[1]
CASES=[
    ('missing_file', 'runs/dev-v2/repeat-0/no_update/original/3/result.json'),
    ('file_created', 'runs/dev-v3/repeat-0/no_update/original/3/result.json'),
]

if __name__=='__main__':
    evaluator=OfficialEvaluator(ROOT/'upstream')
    for label,relative in CASES:
        case=json.loads((ROOT/relative).read_text(encoding='utf-8'))
        model=LocalModel('http://127.0.0.1:8082/v1','qwen2.5-7b-judge',max_tokens=2048)
        result=evaluator.judge(case,list(case['knowledge']['tools'].values()),model)
        save(ROOT/'artifacts/judge-calibration'/f'{label}.json',
             {'source':relative,'split':'development','known_artifact_condition':label,
              'evaluation':result,'model_calls':model.calls})
        print(json.dumps({'case':label,'scores':result['aggregate']},ensure_ascii=True),flush=True)
