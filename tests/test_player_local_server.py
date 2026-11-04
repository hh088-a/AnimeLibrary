import importlib.util,sys,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'player'))
import potplayer_local_server as s

class Tests(unittest.TestCase):
    def test_native_and_pinned_browser_auth(self):
        token='unit-test-only'
        self.assertTrue(s.authorized(None,'Bearer '+token,token))
        self.assertTrue(s.authorized(s.ORIGIN,'Bearer '+token,token))
        for origin in ('null','http://evil.example','http://localhost:8097'):
            self.assertFalse(s.authorized(origin,'Bearer '+token,token))
        self.assertFalse(s.authorized(None,'Bearer wrong',token))
        self.assertFalse(s.authorized(None,'',''))
    def test_fixed_argument_launch(self):
        path='X:/动漫/电影/中文 & 空格.mkv'
        with patch.object(s.Path,'is_file',return_value=True),patch.object(s.subprocess,'Popen') as p:
            p.return_value.pid=99
            self.assertEqual(s.launch({'uri':'playbridge:///'+quote(path,safe='/')})['pid'],99)
            args=p.call_args.args[0]
            self.assertEqual(args,[str(s.bridge.PLAYER),path.replace('/','\\'),'/current'])
            self.assertNotIn('shell',p.call_args.kwargs)
    def test_untrusted_request_does_not_spawn(self):
        with patch.object(s.subprocess,'Popen') as p:
            for data in (None,{}, {'uri':'https://example.com/a.mkv'}, {'uri':'playbridge:///C%3A/Windows/cmd.exe'}, {'uri':'x','extra':True}):
                with self.subTest(data=data),self.assertRaises((ValueError,TypeError)):
                    s.launch(data)
            p.assert_not_called()
    def test_single_listener(self):
        first=s.LocalServer(('127.0.0.1',0),s.Handler)
        try:
            with self.assertRaises(OSError):s.LocalServer(first.server_address,s.Handler)
        finally:first.server_close()

if __name__=='__main__':unittest.main()
