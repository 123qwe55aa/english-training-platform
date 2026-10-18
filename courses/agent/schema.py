"""Small explicit JSON-schema subset; reject coercion and unknown fields."""
import re

class ToolError(Exception):
    def __init__(self,code,message,details=None):
        self.code=code;self.message=message;self.details=details
        super().__init__(message)

def obj(properties,required=()):return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}
def text(maximum=10000):return {'type':'string','maxLength':maximum}
def integer(minimum=1,maximum=2147483647):return {'type':'integer','minimum':minimum,'maximum':maximum}
def array(items,maximum=200):return {'type':'array','items':items,'maxItems':maximum}
BOOL={'type':'boolean'}
ID=integer()
REV=text(64)

def validate(value,schema,path='arguments'):
    kind=schema['type']
    good={'object':lambda:type(value)is dict,'array':lambda:type(value)is list,'string':lambda:type(value)is str,'integer':lambda:type(value)is int,'boolean':lambda:type(value)is bool}[kind]()
    if not good:raise ToolError('invalid_arguments',f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:raise ToolError('invalid_arguments',f'{path}: invalid choice')
    if kind=='object':
        extra=set(value)-set(schema['properties'])
        missing=set(schema.get('required',[]))-set(value)
        if extra or missing:raise ToolError('invalid_arguments',f'{path}: unknown fields {sorted(extra)}; missing {sorted(missing)}')
        for key,item in value.items():validate(item,schema['properties'][key],path+'.'+key)
    if kind=='array':
        if len(value)>schema.get('maxItems',200):raise ToolError('invalid_arguments',f'{path}: too many items')
        for i,item in enumerate(value):validate(item,schema['items'],f'{path}[{i}]')
    if kind=='string' and 'pattern' in schema and not re.search(schema['pattern'],value):raise ToolError('invalid_arguments',f'{path}: invalid text format')
    if kind=='string' and len(value)>schema.get('maxLength',10000):raise ToolError('invalid_arguments',f'{path}: text too long')
    if kind=='integer' and not schema.get('minimum',value)<=value<=schema.get('maximum',value):raise ToolError('invalid_arguments',f'{path}: number outside allowed range')
