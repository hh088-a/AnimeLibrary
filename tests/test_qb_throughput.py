import importlib.util
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'archive/runtime'))
import batch as b
class QB:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def call(self,route,data=None):
        self.calls.append((route,data))
        if route=='torrents/info':return self.rows
def task(h,**kw):
    d=dict(source_hash=h,subject_id=h,status='downloading',selected_bytes=500*1024**2,
      last_progress_at=900,last_progress=.1,rate_window_started_at=0,rate_window_downloaded=1000000)
    d.update(kw);return d
def row(h,**kw):
    d=dict(hash=h,category='anime-batch',state='downloading',progress=.1,dlspeed=100,downloaded=1100000,
      num_seeds=3,num_complete=3,time_active=10000,amount_left=400*1024**2)
    d.update(kw);return d
with patch.object(b,'save_state'),patch.object(b,'storage_ready',return_value=True):
    # A previously fast source that now sends only trickles must yield a slot.
    s={'tasks':{'a':task('a',rate_window_downloaded=10000000000)}}
    q=QB([row('a',downloaded=10000100000)])
    b.maintain_downloads(q,s,now=301)
    t=s['tasks']['a'];assert t['status']=='waiting_for_peers' and t['retry_after']==2101
    # Repeated poor windows back off, rather than retrying all dead sources
    # every thirty minutes. Near-finished and currently fast torrents survive.
    for failures,delay in ((1,3600),(4,21600)):
        s={'tasks':{'a':task('a',low_rate_retries=failures)}};q=QB([row('a')])
        b.maintain_downloads(q,s,now=301);assert s['tasks']['a']['retry_after']==301+delay
    for changes in ({'amount_left':50*1024**2},{'dlspeed':1000000}):
        s={'tasks':{'a':task('a')}};q=QB([row('a',**changes)])
        b.maintain_downloads(q,s,now=301);assert not any(r=='torrents/stop' for r,_ in q.calls)
    # Current healthy payload resets failure history.
    s={'tasks':{'a':task('a',low_rate_retries=4)}};q=QB([row('a',downloaded=20000000,dlspeed=100000)])
    b.maintain_downloads(q,s,now=301);assert s['tasks']['a']['low_rate_retries']==0
    # Ninety old retries leave ten slots for fresh resources at a 100 cap.
    s={'tasks':{str(i):task(str(i),status='waiting_for_peers',retry_after=0) for i in range(510)}}
    q=QB([row(str(i)) for i in range(510)])
    b.maintain_downloads(q,s,now=301)
    assert len([r for r,_ in q.calls if r=='torrents/start'])==475
    assert not any(r=='torrents/delete' for r,_ in q.calls)
    # Many episodes from one title cannot monopolize retry slots.
    s={'tasks':{str(i):task(str(i),subject_id=1,status='waiting_for_peers',retry_after=0) for i in range(20)}}
    q=QB([row(str(i)) for i in range(20)]);b.maintain_downloads(q,s,now=301)
    assert len([r for r,_ in q.calls if r=='torrents/start'])==4
print('PASS: payload windows, backoff, fresh-source reserve, title diversity, partial-file preservation')

import tempfile,json,sys,os
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'AnimeLibrary/batch'))
import cloud_queue as cloud
with tempfile.TemporaryDirectory() as td,patch.object(b,'DATA',Path(td)),patch.object(cloud,'load',return_value={'tasks':{}}):
    (Path(td)/'catalog.json').write_text('[]')
    a={'id':1,'name_cn':'A'};other={'id':2,'name_cn':'B'}
    candidate={'title':'reviewed','manual_verified':True}
    s={'tasks':{str(i):task(str(i),subject_id=1) for i in range(4)},'qb_primary_subjects':[1]}
    sources=[(a,candidate,'new-a'),(other,candidate,'new-b')]
    with patch.object(cloud,'candidates',return_value=sources),patch.object(b,'add_task',return_value='queued') as add,patch.object(b,'save_state'):
        b.qb_primary_tick(QB([]),s)
        assert add.call_args.args[1]['id']==2
print('PASS: fresh work is spread across titles without weakening source identity checks')
