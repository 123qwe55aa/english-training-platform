from django.core.exceptions import ValidationError
from courses.models import Student,Course,Session,Lesson,RewardEntry
from .snapshots import snapshot,get,revision
from .schema import ToolError

def urls(student):return {'public':f'/s/{student.slug}/','admin':f'/admin/courses/student/{student.pk}/change/'}
def student_list(args,ctx):return {'students':[dict(snapshot(s),links=urls(s)) for s in Student.objects.all()]},{}
def student_get(args,ctx):
    from courses.views import progress_context
    from .teaching import session_snapshot
    student=get(Student,args['student_id']);progress=progress_context(student)
    sessions=student.sessions.order_by('-number')[:10]
    return {'student':snapshot(student),'courses':[snapshot(c) for c in student.courses.all()],'recent_sessions':[session_snapshot(s) for s in sessions], 'next_session':session_snapshot(student.sessions.exclude(status='completed').order_by('number').first()) if student.sessions.exclude(status='completed').exists() else None,'recorded_progress':{'completed_sessions':student.sessions.filter(status='completed').count(),'completed_lessons':Lesson.objects.filter(session__student=student,session__status='completed').distinct().count()}, 'progress':{k:progress[k] for k in ['completed_sessions','completed_lessons','planned_sessions','planned_lessons']},'recent_teacher_rewards':[snapshot(r) for r in student.teacher_rewards.all()[:20]],'links':urls(student)},{}

def student_save(args,ctx):
    instance=get(Student,args['student_id']) if args.get('student_id') else Student()
    before=revision(instance,args.get('expected_revision')) if instance.pk else {}
    fields=dict(args['fields']);courses=fields.pop('course_ids',None)
    selected=[get(Course,pk) for pk in courses] if courses is not None else None
    for key,value in fields.items():setattr(instance,key,value)
    instance.full_clean();instance.save()
    if selected is not None:instance.courses.set(selected)
    return {'student':snapshot(instance),'links':urls(instance)},before

def course_list(args,ctx):
    return {'courses':[{'course':snapshot(c),'lessons':[snapshot(l) for l in c.lessons.all()]} for c in Course.objects.all()]},{}
def course_save(args,ctx):
    instance=get(Course,args['course_id']) if args.get('course_id') else Course()
    before=revision(instance,args.get('expected_revision')) if instance.pk else {}
    for key,value in args['fields'].items():setattr(instance,key,value)
    instance.full_clean();instance.save()
    return {'course':snapshot(instance),'admin':f'/admin/courses/course/{instance.pk}/change/'},before
