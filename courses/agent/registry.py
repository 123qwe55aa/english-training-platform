from .schema import obj,text,integer,array,BOOL,ID,REV
from .students import student_list,student_get,student_save,course_list,course_save
STUDENT_FIELDS=obj({'name':text(80),'goal':text(),'schedule':text(100),'published':BOOL,'planned_sessions':integer(),'planned_lessons':integer(0),'reward_label':text(80),'daily_goal':integer(1,100000),'low_threshold':integer(0,50000),'video_points':integer(1,1000),'dialogue_points':integer(1,1000),'course_ids':array(ID)})
TOOLS={}
def register(name,description,schema,handler,write=False):TOOLS[name]={'name':name,'description':description,'input_schema':schema,'write':write,'handler':handler}
register('students.list','List teacher-visible student profiles and revisions.',obj({}),student_list)
register('students.get','Read student assignments, actual progress and recent teaching context.',obj({'student_id':ID},['student_id']),student_get)
register('students.save','Create/update a student. Existing profiles require expected_revision. Draft by default.',obj({'student_id':ID,'expected_revision':REV,'fields':STUDENT_FIELDS},['fields']),student_save,True)
register('courses.list','List all courses and lessons, including drafts.',obj({}),course_list)
register('courses.save','Create/update course metadata without replacing lessons.',obj({'course_id':ID,'expected_revision':REV,'fields':obj({'title':text(200),'order':integer(0),'published':BOOL})},['fields']),course_save,True)
from .materials import material_get,material_import
from .teaching import session_get,session_prepare,session_progress,reward_award,operation_list
BLOCK=obj({'title':text(200),'kind':{'type':'string','enum':['text','video','audio','image','document','dialogue','quiz']},'order':integer(0),'published':BOOL,'upload_handle':text(50),'text':text(500000),'question':text(),'options':array({'type':'string','maxLength':1000,'pattern':r'^[^\r\n\v\f\x1c-\x1e\x85\u2028\u2029]+$','description':'One nonempty single-line option per item; no line separators.'},30),'correct_choice':integer(1,30),'explanation':text()},['title','kind'])
register('materials.get','Read a lesson, all generic blocks and original VOA data; returns aggregate material revision.',obj({'lesson_id':ID},['lesson_id']),material_get)
register('materials.import','Create a lesson or append blocks; never replace VOA data. Files use private upload handles. Existing lesson needs material revision.',obj({'lesson_id':ID,'course_id':ID,'expected_revision':REV,'fields':obj({'number':integer(),'title':text(200),'source_url':text(200),'learning_target':text(),'published':BOOL}),'blocks':array(BLOCK,100)},['fields','blocks']),material_import,True)
EXPRESSION=obj({'en':text(2000),'zh':text(2000)},['en','zh'])
ACTIVITY=obj({'title':text(200),'minutes':integer(1,60),'instruction':text(),'prompt':text(),'task':text()},['title','minutes','instruction'])
SESSION_FIELDS=obj({'title':text(200),'subtitle':text(200),'published':BOOL,'goal':text(),'review_sentences':array(text(2000),6),'expressions':array(EXPRESSION,40),'activities':array(ACTIVITY,30),'b_plan':text(),'exit_check':text()})
register('sessions.get','Read full private classroom, mastery observations and aggregate session revision.',obj({'session_id':ID},['session_id']),session_get)
register('sessions.prepare','Create/update a complete 60-minute teaching plan with prior-day review, B plan and exit check. Does not mark class completed.',obj({'session_id':ID,'expected_revision':REV,'student_id':ID,'number':integer(),'lesson_ids':array(ID,20),'fields':SESSION_FIELDS},['student_id','number','lesson_ids','fields']),session_prepare,True)
MASTERY=obj({'task':text(200),'state':{'type':'string','enum':['independent','prompted','practice']},'evidence':text()},['task','state','evidence'])
register('sessions.progress','Record teacher-confirmed status/date and optional actual mastery evidence; requires current session revision.',obj({'session_id':ID,'expected_revision':REV,'status':{'type':'string','enum':['planned','prepared','completed']},'date':text(10),'evidence':text(),'teacher_reflection':text(),'mastery':array(MASTERY,100)},['session_id','expected_revision','status','evidence']),session_progress,True)
register('rewards.award','Create a dated teacher award or negative correction; requires actual evidence and an idempotency request ID.',obj({'student_id':ID,'date':text(10),'title':text(200),'amount':integer(-100000,100000),'evidence':text()},['student_id','date','title','amount','evidence']),reward_award,True)
register('operations.list','Inspect private audit history or recover a result after a transport failure.',obj({'request_id':text(100),'limit':integer(1,100)}),operation_list)
