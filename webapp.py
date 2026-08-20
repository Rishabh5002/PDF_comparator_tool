"""Dependency-free localhost web UI for the offline comparison engine."""
from __future__ import annotations
import html, json, mimetypes, secrets, shutil, tempfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.comparator.comparator import FormComparator
from src.evaluation import evaluate_matching
from src.parser.form_parser import parse_pdf
from src.reporter.excel_report import write_excel_report
from src.reporter.html_report import write_html_report
from src.reporter.pdf_report import write_pdf_report
from src.security import security_status, verify_offline_core
from src.summary import build_local_summary
from src.matcher import match_diagnostics, match_questions

BASE_DIR=Path(__file__).resolve().parent
RUNTIME_DIR=BASE_DIR/'.runtime'; RUNTIME_DIR.mkdir(exist_ok=True)
MAX_SIZE=50*1024*1024


def _question_dict(q):
    return {
        'number': q.number, 'text': q.text, 'field_type': q.field_type,
        'options': list(q.options or []), 'child_questions': list(q.child_questions or []),
        'page': q.page, 'y': q.y,
    }


def _question_pairs(old_questions, new_questions, threshold):
    matches, removed, added = match_questions(old_questions, new_questions, threshold=threshold)
    pairs = []
    for old, new, score, signals in matches:
        changed = not FormComparator.cosmetic_text_equivalent(old.text, new.text)
        old_opts = {str(x).strip().lower() for x in old.options or [] if str(x).strip()}
        new_opts = {str(x).strip().lower() for x in new.options or [] if str(x).strip()}
        changed = changed or old_opts != new_opts or old.field_type != new.field_type or set(old.child_questions or []) != set(new.child_questions or []) or old.number != new.number
        pairs.append({'matched': True, 'changed': changed, 'old': _question_dict(old), 'new': _question_dict(new), 'score': score, 'signals': signals})
    for old in removed:
        pairs.append({'matched': False, 'side': 'old', 'old': _question_dict(old), 'new': None, 'score': 0, 'signals': {}})
    for new in added:
        pairs.append({'matched': False, 'side': 'new', 'old': None, 'new': _question_dict(new), 'score': 0, 'signals': {}})
    pairs.sort(key=lambda p: (p['old']['number'] if p.get('old') else 10**9, p['new']['number'] if p.get('new') else 10**9))
    return pairs


def build_payload(old_path,new_path,old_password,new_password,threshold):
    old=parse_pdf(old_path,old_password,max_size_bytes=MAX_SIZE)
    new=parse_pdf(new_path,new_password,max_size_bytes=MAX_SIZE)
    result=FormComparator(match_threshold=threshold).compare(old['questions'],new['questions'])
    return {'mode':'offline','security':security_status(),'offline_verification':verify_offline_core(),
      'old_document':{'filename':old['filename'],'pages':old['page_count'],'questions':len(old['questions']),'encrypted':old['encrypted']},
      'new_document':{'filename':new['filename'],'pages':new['page_count'],'questions':len(new['questions']),'encrypted':new['encrypted']},
      'comparison':result.to_dict(),'local_summary':build_local_summary(result),
      'question_pairs':_question_pairs(old['questions'],new['questions'],threshold),
      'matching_diagnostics':match_diagnostics(old['questions'],new['questions'],threshold=threshold),
      'evaluation':evaluate_matching(old['questions'],new['questions'],threshold=threshold)}


def write_reports(payload,workdir):
    base=workdir/'comparison'; paths={}
    jsonp=base.with_suffix('.json'); htmlp=base.with_suffix('.html'); pdfp=base.with_suffix('.pdf'); xlsx=base.with_suffix('.xlsx')
    jsonp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    write_html_report(payload,htmlp); write_pdf_report(payload,pdfp); write_excel_report(payload,xlsx)
    return {p.suffix[1:]:p for p in (jsonp,htmlp,pdfp,xlsx)}


def parse_multipart(content_type, body):
    # Uses the standard-library MIME parser; no third-party web framework required.
    msg=BytesParser(policy=default).parsebytes((f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
    fields={}
    for part in msg.iter_parts():
        disp=part.get('Content-Disposition','')
        params=dict(part.get_params(header='content-disposition',failobj=[]))
        name=params.get('name'); filename=params.get('filename')
        if not name: continue
        data=part.get_payload(decode=True) or b''
        fields[name]={'filename':filename,'data':data,'text':data.decode(part.get_content_charset() or 'utf-8','replace')}
    return fields


def html_page():
    return (BASE_DIR/'templates'/'index.html').read_text(encoding='utf-8')

class Handler(BaseHTTPRequestHandler):
    server_version='FormDiff/1.0'
    def _send(self,status,ctype,body,extra=None):
        if isinstance(body,str): body=body.encode()
        self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        if extra:
            for k,v in extra.items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/': return self._send(200,'text/html; charset=utf-8',html_page())
        if path=='/static/app.css': return self._send(200,'text/css; charset=utf-8',(BASE_DIR/'static/app.css').read_text())
        if path=='/static/app.js': return self._send(200,'application/javascript; charset=utf-8',(BASE_DIR/'static/app.js').read_text())
        if path=='/api/health': return self._json(200,{'status':'ok','mode':'offline','security':security_status(),'offline':verify_offline_core()})
        if path.startswith('/api/report/'):
            bits=path.split('/')
            if len(bits)!=5: return self._json(404,{'error':'Report not found.'})
            token,kind=bits[3],bits[4]
            if kind not in {'json','html','pdf','xlsx'}: return self._json(404,{'error':'Unsupported report format.'})
            p=RUNTIME_DIR/token/f'comparison.{kind}'
            if not p.is_file(): return self._json(404,{'error':'Report not found or expired.'})
            data=p.read_bytes(); ctype={'json':'application/json','html':'text/html','pdf':'application/pdf','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}[kind]
            return self._send(200,ctype,data,{'Content-Disposition':f'attachment; filename="comparison.{kind}"'})
        return self._json(404,{'error':'Not found.'})
    def do_POST(self):
        if urlparse(self.path).path!='/api/compare': return self._json(404,{'error':'Not found.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>2*MAX_SIZE: raise ValueError('Upload exceeds the request size limit.')
            body=self.rfile.read(length)
            fields=parse_multipart(self.headers.get('Content-Type',''),body)
            workdir=Path(tempfile.mkdtemp(prefix='fpct_',dir=RUNTIME_DIR))
            old=self._save(fields.get('old_pdf'),workdir,'Original'); new=self._save(fields.get('new_pdf'),workdir,'Revised')
            oldpw=fields.get('old_password',{}).get('text') or None; newpw=fields.get('new_password',{}).get('text') or None
            try: threshold=float(fields.get('threshold',{}).get('text','0.45'))
            except ValueError: threshold=.45
            threshold=min(max(threshold,0),1)
            payload=build_payload(old,new,oldpw,newpw,threshold)
            paths=write_reports(payload,workdir); token=workdir.name
            reports={k:f'/api/report/{token}/{k}' for k in paths}
            return self._json(200,{'ok':True,'token':token,'payload':payload,'reports':reports})
        except Exception as exc:
            return self._json(400,{'ok':False,'error':str(exc)})
    def _save(self,field,workdir,label):
        if not field or not field.get('filename'): raise ValueError(f'{label} PDF is required.')
        name=Path(field['filename']).name
        if Path(name).suffix.lower()!='.pdf': raise ValueError(f'{label} must be a PDF file.')
        data=field.get('data',b'')
        if len(data)>MAX_SIZE: raise ValueError(f'{label} PDF exceeds the 50 MB limit.')
        target=workdir/(secrets.token_hex(8)+'_'+name); target.write_bytes(data); return target
    def _json(self,status,obj): return self._send(status,'application/json; charset=utf-8',json.dumps(obj,ensure_ascii=False))
    def log_message(self,fmt,*args): print('[FormDiff]',fmt%args)


def run(host='127.0.0.1',port=8000):
    print(f'FormDiff running at http://{host}:{port}')
    print('Local-only server: it binds to 127.0.0.1 and uses no cloud API.')
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=='__main__': run()
