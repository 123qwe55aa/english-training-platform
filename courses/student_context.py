from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from .models import Student,Course

def resolve_student(request,slug=None):
    student=get_object_or_404(Student,slug=slug or 'learner',published=True)
    request.learning_student=student
    request.student_prefix=f'/s/{student.slug}' if slug else ''
    return student

def student_courses(student):
    return student.courses.filter(published=True)

def reward_config(student,prefix=''):
    day=timezone.localdate()
    return {'studentId':student.pk,'studentName':student.name,'label':student.reward_name,'goal':student.daily_goal,'halfGoal':student.daily_goal/2,'lowThreshold':student.low_threshold,'videoPoints':student.video_points,'dialoguePoints':student.dialogue_points,'teacherPoints':student.teacher_rewards.filter(date=day).aggregate(total=Sum('amount'))['total'] or 0,'date':day.isoformat(),'legacyLearner':student.slug=='learner','summaryUrl':prefix+'/rewards/summary/'}

def context(request):
    student=getattr(request,'learning_student',None)
    if not student:return {}
    prefix=request.student_prefix
    return {'student':student,'student_prefix':prefix,'public_students':Student.objects.filter(published=True),'reward_config':reward_config(student,prefix)}
