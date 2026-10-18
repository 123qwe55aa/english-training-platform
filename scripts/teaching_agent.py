#!/usr/bin/env python3
"""Codex CLI: private JSON tools via existing SSH; no external dependencies."""
import argparse,json,os,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOST=os.getenv('ENGLISH_PLATFORM_SSH_TARGET')
REMOTE=os.getenv('ENGLISH_PLATFORM_REMOTE_DIR')

def command(local=False,upload=None):
    tail=['python','manage.py','agent_tool']
    if upload:tail+=['--upload-name',upload.name,'--size',str(upload.stat().st_size)]
    if local:return [sys.executable,str(ROOT/'manage.py'),*tail[2:]]
    if not HOST or not REMOTE:
        raise RuntimeError('Set ENGLISH_PLATFORM_SSH_TARGET and ENGLISH_PLATFORM_REMOTE_DIR before using remote mode.')
    return ['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',HOST,'cd '+shlex.quote(REMOTE)+' && '+shlex.join(['docker','compose','exec','-T','app',*tail])]

def send(request=None,upload=None,local=False):
    stream=None
    try:
        if upload:
            stream=upload.open('rb')
            result=subprocess.run(command(local,upload),stdin=stream,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3600)
        else:
            result=subprocess.run(command(local),input=json.dumps(request,ensure_ascii=False).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)
        if result.returncode:raise RuntimeError('SSH/management command failed; no success has been confirmed.')
        try:output=json.loads(result.stdout)
        except (ValueError,UnicodeError):raise RuntimeError('Server returned no valid JSON result; check audit history before retrying.')
        return output
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        return {'ok':False,'error':{'code':'transport_error','message':str(exc),'request_id':(request or {}).get('request_id'),'retry':'Query operations.list, or retry exactly the same request ID and arguments; do not issue a fresh award request.'}}
    finally:
        if stream:stream.close()

def load(path):
    return json.loads(sys.stdin.read() if path=='-' else Path(path).read_text())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local',action='store_true',help='Use explicitly configured local Django database for testing.')
    sub=parser.add_subparsers(dest='mode',required=True)
    sub.add_parser('tools',help='Discover tool descriptions and JSON argument schemas.')
    call=sub.add_parser('call');call.add_argument('tool');call.add_argument('--args',help='Arguments JSON file, or - for stdin.');call.add_argument('--request-id');call.add_argument('--apply',action='store_true')
    upload=sub.add_parser('upload');upload.add_argument('file',type=Path)
    raw=sub.add_parser('request');raw.add_argument('--input',default='-')
    args=parser.parse_args()
    try:
        if args.mode=='upload':response=send(upload=args.file.resolve(),local=args.local)
        else:
            request=load(args.input) if args.mode=='request' else {'tool':'tools.list' if args.mode=='tools' else args.tool,'arguments':load(args.args) if args.mode=='call' and args.args else {}}
            if args.mode=='call':
                if args.request_id:request['request_id']=args.request_id
                request['apply']=args.apply
            response=send(request=request,local=args.local)
    except (OSError,ValueError) as exc:response={'ok':False,'error':{'code':'invalid_input','message':str(exc)}}
    print(json.dumps(response,ensure_ascii=False,indent=2))
    return 0 if response.get('ok') else 1

if __name__=='__main__':sys.exit(main())
