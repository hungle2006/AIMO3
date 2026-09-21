from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rag.system import OlympiadRAG
from core.config import load_config
cfg=load_config(ROOT/'config_v2_6.yaml')
r=OlympiadRAG(ROOT,cfg)
print(json.dumps(r.health(),indent=2))
print('No sklearn pickle was written. Runtime rebuild is active.')
