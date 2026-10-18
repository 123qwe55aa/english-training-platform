import hashlib,json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ObjectDoesNotExist
from .schema import ToolError

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),cls=DjangoJSONEncoder)
def snapshot(instance):
    data={f.name:(str(getattr(instance,f.attname)) if f.get_internal_type()=='FileField' else getattr(instance,f.attname)) for f in instance._meta.concrete_fields}
    for field in instance._meta.many_to_many:data[field.name]=sorted(getattr(instance,field.name).values_list('pk',flat=True))
    data=json.loads(canonical(data))
    data['revision']=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def get(model,pk):
    try:return model.objects.get(pk=pk)
    except ObjectDoesNotExist:raise ToolError('not_found',f'{model.__name__} {pk} does not exist')

def revision(instance,expected):
    current=snapshot(instance)
    if not expected or expected!=current['revision']:raise ToolError('stale_revision','Read the current record and supply its expected_revision.',{'current_revision':current['revision']})
    return current
