from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.parsing import parse_constraint_formalization, formalization_is_usable

raw = r'''{
  "entities":["Alice","Bob"],
  "variables":[
    {"name":"a","owner":"Alice","kind":"sweets","domain":"integer"},
    {"name":"b","owner":"Bob","kind":"sweets","domain":"integer"},
    {"name":"x","owner":"Alice","kind":"age","domain":"positive integer"},
    {"name":"y","owner":"Bob","kind":"age","domain":"positive integer"}
  ],
  "pre_relations":[
    {"type":"sum_ratio","left":"Alice","right":"Bob","factor":2,"operands":["age","sweets"]}
  ],
  "events":[{"type":"transfer","asset":"sweets","amount":5,"from":"Alice","to":"Bob"}],
  "post_equalities":[{"type":"sum_equal","left":"Alice","right":"Bob","operands":["age","sweets"]}],
  "goal":{"type":"product","terms":["Alice.age","Bob.age"]},
  "ambiguity":"NONE"
}'''
f = parse_constraint_formalization(raw)
assert f["parse_ok"] is True, f
assert formalization_is_usable(f) is True, f

bad = parse_constraint_formalization('{"entities":[],"variables":[],"pre_relations":[],"events":[],"post_equalities":[],"goal":{},"ambiguity":"NONE"}')
assert formalization_is_usable(bad) is False
print("test_constraint_parser: PASS")
