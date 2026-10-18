"""Teacher-only operations invoked by a management command over existing SSH."""
import hashlib,logging
from django.db import transaction,IntegrityError,OperationalError
from django.core.exceptions import ValidationError
from courses.models import AgentOperation
from .snapshots import canonical
from .schema import ToolError,validate,obj,text,BOOL
from .registry import TOOLS
logger=logging.getLogger(__name__)

def execute(request):
    ctx={'files':[],'consume':[]};committed=False
    try:
        if type(request)is not dict:raise ToolError('invalid_request','Request must be an object.')
        extra=set(request)-{'tool','arguments','request_id','apply'}
        if extra:raise ToolError('invalid_request','Unknown request fields: '+', '.join(sorted(extra)))
        name=request.get('tool');args=request.get('arguments',{});apply=request.get('apply',False)
        if type(apply)is not bool:raise ToolError('invalid_request','apply must be boolean; default false.')
        if name=='tools.list':
            validate(args,obj({}))
            return {'ok':True,'result':{'version':1,'transport':'authenticated SSH management command','writes_default':'dry-run','tools':[{k:v for k,v in tool.items() if k!='handler'} for tool in TOOLS.values()]}}
        if type(name)is not str or name not in TOOLS:raise ToolError('unknown_tool','Use tools.list to discover supported operations.')
        tool=TOOLS[name];validate(args,tool['input_schema'])
        if not tool['write']:
            result,_=tool['handler'](args,ctx)
            return {'ok':True,'result':result}
        request_id=request.get('request_id')
        if not isinstance(request_id,str) or not request_id.strip() or len(request_id)>100:raise ToolError('invalid_request','Writes require a nonempty request_id of at most 100 characters.')
        fingerprint=hashlib.sha256(canonical({'tool':name,'arguments':args}).encode()).hexdigest()
        with transaction.atomic():
            previous=AgentOperation.objects.filter(request_id=request_id).first()
            if previous:
                if previous.fingerprint!=fingerprint:raise ToolError('idempotency_conflict','request_id already used for different arguments.')
                return {'ok':True,'result':previous.result,'operation_id':previous.pk,'replayed':True,'dry_run':False}
            operation=AgentOperation.objects.create(request_id=request_id,tool=name,fingerprint=fingerprint,arguments=args) if apply else None
            result,before=tool['handler'](args,ctx)
            # Normalize dates before JSONField storage and transport.
            import json
            result=json.loads(canonical(result));before=json.loads(canonical(before))
            if apply:
                operation.before=before;operation.after=result;operation.result=result;operation.save(update_fields=['before','after','result'])
            else:transaction.set_rollback(True)
        committed=apply
        if apply:
            for upload in ctx['consume']:
                try:upload.unlink(missing_ok=True)
                except OSError:logger.warning('Staged upload cleanup deferred')
        return {'ok':True,'result':result,'changes':{'before':before,'after':result},'operation_id':operation.pk if operation else None,'dry_run':not apply,'replayed':False}
    except ToolError as exc:return {'ok':False,'error':{'code':exc.code,'message':exc.message,'details':exc.details}}
    except ValidationError as exc:return {'ok':False,'error':{'code':'validation_error','message':'The operation failed validation.','details':getattr(exc,'message_dict',exc.messages)}}
    except (IntegrityError,OperationalError):return {'ok':False,'error':{'code':'conflict','message':'Concurrent write or duplicate record. Read current state; retry the same request ID if transport failed.'}}
    finally:
        # Filesystem writes are not transactional. Remove only files created by this request.
        if not committed:
            for file in ctx['files']:file.storage.delete(file.name)
