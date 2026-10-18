from copy import deepcopy
from django.db import transaction

@transaction.atomic
def copy_plan(source,target):
    from .models import Session
    if source.pk==target.pk:return 0
    allowed=set(target.courses.values_list('pk',flat=True))
    copied=0
    fields=['title','subtitle','goal','review_sentences','expressions','activities','b_plan','exit_check','published']
    for session in source.sessions.prefetch_related('lessons'):
        lessons=[l for l in session.lessons.all() if l.course_id in allowed]
        if not lessons:continue
        values={f:deepcopy(getattr(session,f)) for f in fields}
        new,created=Session.objects.get_or_create(student=target,number=session.number,defaults={**values,'status':'planned','date':None,'teacher_reflection':''})
        if created:new.lessons.set(lessons);copied+=1
    return copied
