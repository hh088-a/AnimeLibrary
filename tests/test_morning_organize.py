import importlib.util,json,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'archive/runtime'))
import organize_cloud_batch as m,library_watch as w
with tempfile.TemporaryDirectory() as td:
    m.FOLDER=Path(td)
    for sid,prefix in ((475032,'Kamitsubaki City Under Construction'),(566600,'Towa no Yuugure')):
        s=dict(id=sid,name='Test',name_cn='Test',eps=13,tmdb='tv/123',_review_allow_gaps=True)
        for nums in ([0],[0,1,2,12],[2,3]):
            items=[dict(dir=False,id=str(i),size=1,sha1='A'*40,name=f'{prefix} - {n:02d} [1080p].mkv',path=f'/stage/{prefix} - {n:02d} [1080p].mkv') for i,n in enumerate(nums)]
            corrected=w.reviewed_subject(s,items)
            (m.FOLDER/(str(sid)+'.before.json')).write_text(json.dumps(items),encoding='utf8')
            plan=m.build([dict(subject=corrected,tasks=[dict(hash='a',destination='/stage')])],persist=False)[0]
            transfers=plan['transfers'];assert len(transfers)==len(nums)
            for n,x in zip(nums,transfers):
                assert ('/Season 00/' in x['destination'])==(n==0)
                assert f'S{0 if n==0 else 1:02d}E{1 if n==0 else n:02d}.mkv' in x['destination']
        unknown=w.reviewed_subject(s,[dict(dir=False,name='Other show - 00 [1080p].mkv')])
        assert not unknown.get('_review_special_episode_map')
    s=dict(id=529431,name='Dandadan',eps=12,tmdb='tv/240411/season/1/episode/13',_review_allow_gaps=True)
    v=dict(dir=False,name='[Feibanyama] Dan Da Dan S2 - 02 [1080p].mkv',path='/stage/[Feibanyama] Dan Da Dan S2 - 02 [1080p].mkv')
    fixed=w.reviewed_subject(s,[v]);dest,_=m.classify(fixed,v,'/stage')
    assert 'S01E14' in dest
print('PASS: zero prologues do not shift regular episodes; single specials accepted; partial S2 stays correctly numbered; unknown sources unchanged')
