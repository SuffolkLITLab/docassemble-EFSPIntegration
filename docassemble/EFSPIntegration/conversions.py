from datetime import datetime
from docassemble.base.util import DADateTime, as_datetime
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

def pretty_display(data, tab_depth=0):
  tab_inc = 4
  out = ''
  if isinstance(data, list):
    for idx, elem in enumerate(data):
      out += (' ' * tab_depth) + f'* idx: {idx}\n'
      out += pretty_display(elem, tab_depth + tab_inc)

  elif isinstance(data, dict):
    for key, val in data.items():
      if val is not None and val != []:
        out += (' ' * tab_depth) + f'* {key}: \n'
        out += pretty_display(val, tab_depth + tab_inc)
  else:
    out = (' ' * tab_depth) + str(data) + '\n'
  return out

def tyler_timestamp_to_datetime(tyler_timestamp:int)->DADateTime:
  return as_datetime(datetime.utcfromtimestamp(tyler_timestamp/1000))

