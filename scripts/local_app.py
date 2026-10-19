"""Local-only birth form and chart viewer. No external calls or saved birth records."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys

UI = Path(__file__).resolve().parent.parent/'assets/ui/index.html'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Birth information and API bodies are never written to access logs.

    def send(self, status, data, content_type='application/json; charset=utf-8'):
        body = data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if self.path != '/': return self.send(404,{'error':'Not found'})
        return self.send(200,UI.read_bytes(),'text/html; charset=utf-8')

    def do_POST(self):
        if self.path != '/api/chart': return self.send(404,{'error':'Not found'})
        port=self.server.server_port
        permitted={f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
        if self.headers.get('Origin') not in permitted:
            return self.send(403,{'error':'请从本地表单提交。'})
        if self.headers.get_content_type() != 'application/json': return self.send(415,{'error':'JSON required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 65536: raise ValueError('Request size outside limit')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict) or set(body) != {'record','ziwei'} or type(body['ziwei']) is not bool:
                raise ValueError('Invalid form payload')
            command=[sys.executable,'-X','utf8',str(Path(__file__).parent/'chart.py'),'--record','-']
            if body['ziwei']: command.append('--ziwei')
            result=subprocess.run(command,input=json.dumps(body['record']),capture_output=True,
                                  encoding='utf-8',text=True,timeout=90)
            if result.returncode:
                raise ValueError(result.stderr.split('error:')[-1].strip())
            chart=json.loads(result.stdout)
            if body['ziwei']:
                from ziwei_bridge import render_markdown
                markdown=render_markdown(chart)
            else:
                markdown='# 八字排盘\n\n'+'　'.join(chart['central']['pillars'])+'\n\n'+json.dumps(chart,ensure_ascii=False,indent=2)
            self.send(200,{'result':chart,'markdown':markdown})
        except (ValueError,TypeError,OSError,subprocess.TimeoutExpired) as error:
            self.send(400,{'error':str(error)})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8765)
    args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'本地排盘：http://127.0.0.1:{server.server_port}；Ctrl+C退出。出生资料不保存、不上传。',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
