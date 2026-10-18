import json,sys,logging
from django.core.management.base import BaseCommand
from courses.agent.schema import ToolError
from courses.agent.service import execute
from courses.agent.snapshots import canonical
from courses.agent.uploads import stage
logger=logging.getLogger(__name__)

class Command(BaseCommand):
    help='Teacher-only JSON tools over SSH. No HTTP endpoint. Writes default to dry-run.'
    requires_system_checks=[]
    stealth_options=('stdin',)
    def add_arguments(self,parser):
        parser.add_argument('--upload-name')
        parser.add_argument('--size',type=int)
    def handle(self,*args,**options):
        stream=options.get('stdin') or sys.stdin
        try:
            if options.get('upload_name'):
                result={'ok':True,'result':stage(getattr(stream,'buffer',stream),options['upload_name'],options.get('size'))}
            else:
                raw=stream.read(8*1024*1024+1)
                if len(raw)>8*1024*1024:raise ToolError('request_too_large','JSON request exceeds 8 MiB.')
                try:request=json.loads(raw,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite number')))
                except (ValueError,UnicodeError):raise ToolError('invalid_json','Send a valid JSON request object.')
                result=execute(request)
        except ToolError as exc:result={'ok':False,'error':{'code':exc.code,'message':exc.message}}
        except Exception:
            logger.exception('Agent tool failed')
            result={'ok':False,'error':{'code':'internal_error','message':'Operation failed. Query operations.list with the same request ID before retrying.'}}
        self.stdout.write(canonical(result))
