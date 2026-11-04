"""Loopback-only external-player bridge with origin and per-install token checks."""
import hmac,json,logging,os,secrets,subprocess,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import socket
from pathlib import Path
import potplayer_bridge as bridge

HOST='127.0.0.1'
PORT=18097
ORIGIN='http://127.0.0.1:8097'
CONFIG=Path(__file__).with_name('local-server.json')
TOKEN=''

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

def authorized(origin,header,token):
    # JMP's native HTTP transport omits Origin. Browser origins remain pinned;
    # native calls still need the unguessable per-install bearer token.
    return origin in (None,ORIGIN) and bool(token) and hmac.compare_digest(header,'Bearer '+token)

def launch(payload):
    if not isinstance(payload,dict) or set(payload)!={'uri'}:raise ValueError('Expected a single video URI')
    video=bridge.parse_uri(payload['uri'])
    if not Path(video).is_file():raise FileNotFoundError('Video unavailable on the X: mount')
    if not bridge.PLAYER.is_file():raise FileNotFoundError('PotPlayer runtime unavailable')
    child=subprocess.Popen([str(bridge.PLAYER),video,'/current'],cwd=bridge.PLAYER.parent)
    logging.info('Player started: %s',video)
    return {'started':True,'pid':child.pid}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send_json(self,status,data):
        body=json.dumps(data).encode('utf-8');self.send_response(status)
        if self.headers.get('Origin')==ORIGIN:self.send_header('Access-Control-Allow-Origin',ORIGIN)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        self.send_json(200 if self.path=='/health' else 404,{'ready':self.path=='/health'})
    def do_OPTIONS(self):
        if self.path!='/play' or self.headers.get('Origin')!=ORIGIN:return self.send_json(403,{'error':'Forbidden origin'})
        self.send_response(204);self.send_header('Access-Control-Allow-Origin',ORIGIN)
        self.send_header('Access-Control-Allow-Methods','POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type')
        self.send_header('Content-Length','0');self.end_headers()
    def do_POST(self):
        if self.path!='/play':return self.send_json(404,{'error':'Unknown endpoint'})
        if not authorized(self.headers.get('Origin'),self.headers.get('Authorization',''),TOKEN):
            logging.info('Rejected request v2: origin=%r origin_ok=%s header_length=%d expected_length=%d',self.headers.get('Origin'),self.headers.get('Origin') in (None,ORIGIN),len(self.headers.get('Authorization','')),len('Bearer '+TOKEN))
            return self.send_json(403,{'error':'Unauthorized'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=16384:raise ValueError('Invalid request length')
            data=launch(json.loads(self.rfile.read(n)))
            self.send_json(200,data)
        except (ValueError,TypeError,FileNotFoundError) as e:self.send_json(400,{'error':str(e)})
        except Exception as e:
            logging.error('Player launch error: %s',type(e).__name__)
            self.send_json(500,{'error':'Player launch failed'})

def main():
    global TOKEN
    config=json.loads(CONFIG.read_text(encoding='utf-8'))
    TOKEN=config['token']
    if config.get('runtime_root'):
        bridge.ROOT=Path(config['runtime_root'])
        bridge.PLAYER=bridge.ROOT/'player/PotPlayer/PotPlayerMini64.exe'
    log=bridge.ROOT/'logs/potplayer-local-server.log';log.parent.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=log,encoding='utf-8',level=logging.INFO,format='%(asctime)s %(message)s')
    try:server=LocalServer((HOST,PORT),Handler)
    except OSError:return
    logging.info('Local player bridge ready on loopback')
    server.serve_forever()

if __name__=='__main__':main()
