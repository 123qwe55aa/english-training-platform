from datetime import date
from django.core.exceptions import ValidationError
from courses.models import Student,Lesson,Session,MasteryRecord,RewardEntry,AgentOperation
from .snapshots import snapshot,get,revision
from .schema import ToolError

def session_snapshot(session):
    import hashlib
    from .snapshots import canonical
    data=snapshot(session);data.pop('revision')
    data['mastery']=[snapshot(m) for m in session.mastery.order_by('id')]
    data['revision']=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def session_get(args,ctx):return {'session':session_snapshot(get(Session,args['session_id']))},{}
def guard_session(session,expected):
    before=session_snapshot(session)
    if before['revision']!=expected:raise ToolError('stale_revision','Read sessions.get and use session.revision.')
    return before

def session_prepare(args,ctx):
    student=get(Student,args['student_id']);number=args['number']
    if args.get('session_id'):
        session=get(Session,args['session_id']);before=guard_session(session,args.get('expected_revision'))
        if session.student_id!=student.pk or session.number!=number:raise ToolError('invalid_arguments','Existing session student/number cannot change.')
    else:
        session=Session(student=student,number=number,status='prepared');before={}
    fields=args['fields']
    for key in ['title','goal','expressions','activities','b_plan','exit_check']:
        value=fields.get(key)
        if not value or (isinstance(value,str) and not value.strip()):raise ToolError('incomplete_lesson',f'Lesson template requires nonempty {key}.')
    if any(not expression['en'].strip() or not expression['zh'].strip() for expression in fields['expressions']):raise ToolError('incomplete_lesson','Each expression needs nonempty English and Chinese text.')
    review=fields.get('review_sentences',[])
    if number>1 and (not 5<=len(review)<=6 or any(not line.strip() for line in review)):raise ToolError('incomplete_lesson','Day 2 onward requires 5-6 actually taught review sentences.')
    if not all(activity.get('title','').strip() and activity.get('instruction','').strip() for activity in fields['activities']) or sum(a['minutes'] for a in fields['activities'])!=60:raise ToolError('incomplete_lesson','Classroom activities must total 60 minutes and include instructions.')
    if not args['lesson_ids']:raise ToolError('incomplete_lesson','Choose the lesson material for this class.')
    lessons=[get(Lesson,pk) for pk in args['lesson_ids']]
    allowed=set(student.courses.values_list('pk',flat=True))
    if any(l.course_id not in allowed for l in lessons):raise ToolError('course_not_assigned','Assign the course to the student before preparing this class.')
    for key,value in fields.items():setattr(session,key,'\n'.join(value) if key=='review_sentences' else value)
    if session.status!='completed':session.status='prepared'
    session.full_clean();session.save();session.lessons.set(lessons)
    return {'session':session_snapshot(session),'public':f'/s/{student.slug}/sessions/{session.pk}/','admin':f'/admin/courses/session/{session.pk}/change/'},before

def parse_date(value):
    try:return date.fromisoformat(value)
    except (TypeError,ValueError):raise ToolError('invalid_arguments','Use a valid ISO date YYYY-MM-DD.')

def session_progress(args,ctx):
    session=get(Session,args['session_id']);before=guard_session(session,args.get('expected_revision'))
    if not args['evidence'].strip():raise ToolError('evidence_required','Supply the teacher-observed evidence; do not infer completion from visits.')
    if args['status']=='completed' and not args.get('date'):raise ToolError('evidence_required','Completion requires the actual class date.')
    session.status=args['status']
    if args.get('date'):session.date=parse_date(args['date'])
    if 'teacher_reflection' in args:session.teacher_reflection=args['teacher_reflection']
    session.full_clean();session.save()
    for item in args.get('mastery',[]):
        if not item['evidence'].strip() or not item['task'].strip():raise ToolError('evidence_required','Each mastery observation needs a task and actual evidence.')
        record=MasteryRecord(session=session,**item);record.full_clean();record.save()
    return {'session':session_snapshot(session),'public':f'/s/{session.student.slug}/progress/'},before

def reward_award(args,ctx):
    if not args['title'].strip() or not args['evidence'].strip():raise ToolError('evidence_required','Award requires a public reason and private teacher evidence.')
    reward=RewardEntry(student=get(Student,args['student_id']),date=parse_date(args['date']),title=args['title'],amount=args['amount'])
    reward.full_clean();reward.save()
    return {'reward':snapshot(reward),'public':f'/s/{reward.student.slug}/progress/','admin':f'/admin/courses/rewardentry/{reward.pk}/change/'},{}

def operation_list(args,ctx):
    query=AgentOperation.objects.all()
    if 'request_id' in args:query=query.filter(request_id=args['request_id'])
    return {'operations':[snapshot(op) for op in query[:args.get('limit',20)]]},{}
