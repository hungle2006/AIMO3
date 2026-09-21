from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.parsing import parse_solver_output
from core.verification import verify_candidate
from core.config import load_config

text = '''[COMMIT]\nCANDIDATE_ANSWER: 37\n[KEY_REDUCTION]\nA short reduction.\n[SOLUTION]\nThe proof continues but is cut off'''
c = parse_solver_output(text, truncated=True)
assert c['candidate_answer'] == 37, c
assert c['commit_answer'] == 37, c
assert c['protocol_complete'] is False, c
assert c['parse_status'] == 'TRUNCATED_WITH_COMMIT', c

cfg = load_config(ROOT / 'config_v2_7_1.yaml')
v = verify_candidate(c, cfg).to_dict()
assert v['passed'] is False, v
assert v['level'] == 'FORMAT', v
print('test_commit_parser_v271: PASS')
