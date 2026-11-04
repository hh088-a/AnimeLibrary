import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'archive/runtime'))
from organize_cloud_batch import subtitle_suffix
# A single episode can ship four subtitle renditions. None may overwrite
# another and only the ordinary simplified track should be default.
tracks=[subtitle_suffix(x) for x in ('chs','cht','chs.al','cht.al')]
assert len(set(tracks))==4
assert tracks==['.zh-Hans.default','.zh-Hant','.zh-Hans.al','.zh-Hant.al']
assert sum('.default' in x for x in tracks)==1
assert subtitle_suffix('CHS.AL')=='.zh-Hans.al'
assert subtitle_suffix('chs.jp')=='.zh-Hans.中日双语.default'
print('PASS: four subtitle variants stay distinct; exactly one default; bilingual naming preserved')
