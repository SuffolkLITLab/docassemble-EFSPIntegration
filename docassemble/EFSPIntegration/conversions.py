from typing import List, Dict, Tuple, Any

def convert_court_to_id(trial_court) -> str:
  # TODO(brycew): actually implement
  if isinstance(trial_court, str):
    return trial_court.lower()
  return str(trial_court.name).lower()
  
def choices_and_map(codes_list:List, display:str=None, backing:str=None) -> Tuple[List[Any], Dict]:
  if display is None:
    display = '{name}'
  if backing is None:
    backing = 'code'
  choices_list = list(map(lambda vv: (vv[backing], display.format(**vv)), codes_list))
  codes_map = { vv[backing] : vv for vv in codes_list }
  return choices_list, codes_map