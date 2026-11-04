import importlib.util,tempfile,time
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

def task(h,status,**kw):
    return dict(source_hash=h,status=status,selected_bytes=1000,last_progress_at=0,last_progress=0,retry_after=0,**kw)
def row(h,**kw):
    return dict(hash=h,category='anime-batch',state='stalledDL',progress=0,dlspeed=0,num_seeds=1,num_complete=2,availability=1,**kw)

with patch.object(b,'save_state'),patch.object(b,'storage_ready',return_value=True),patch.object(b,'MAX_ACTIVE',1):
    # Waiting records precede active ones in real ledgers. A freed slot must be
    # reused in this pass, preferring a known swarm over a seedless early entry.
    s={'tasks':{'dead':task('dead','waiting_for_peers'),'ready':task('ready','waiting_for_peers'),'idle':task('idle','downloading')}}
    r0=row('dead');r0.update(num_complete=0,num_seeds=0,state='stoppedDL')
    r1=row('ready');r1['state']='stoppedDL'
    q=QB([r0,r1,row('idle')]);b.maintain_downloads(q,s,now=2000)
    assert s['tasks']['idle']['status']=='waiting_for_peers'
    assert s['tasks']['ready']['status']=='downloading'
    assert s['tasks']['dead']['status']=='waiting_for_peers'
    assert q.calls.index(('torrents/stop',{'hashes':'idle'}))<q.calls.index(('torrents/start',{'hashes':'ready'}))
    assert b.active_downloads(s)==1 and not any('delete' in c[0] for c in q.calls)
    # A flowing or newly retried source keeps its connection time.
    for extra in ({'dlspeed':100000},{'progress':.25}):
        rr=row('live');rr.update(extra);s={'tasks':{'live':task('live','downloading')}}
        q=QB([rr]);b.maintain_downloads(q,s,now=2000)
        assert not any(c[0]=='torrents/stop' for c in q.calls)
    s={'tasks':{'live':task('live','downloading',retry_grace_until=2100)}}
    q=QB([row('live')]);b.maintain_downloads(q,s,now=2000)
    assert not any(c[0]=='torrents/stop' for c in q.calls)
    # Storage guard and replacement state must remain effective.
    s={'tasks':{'ready':task('ready','waiting_for_peers'),'old':task('old','source_replaced')}}
    q=QB([row('ready'),row('old')])
    with patch.object(b,'storage_ready',return_value=False):b.maintain_downloads(q,s,now=2000)
    assert not any(c[0]=='torrents/start' for c in q.calls)
print('PASS: seeded retry priority, same-cycle slot reuse, progress/grace/storage/replacement guards, no deletion')
