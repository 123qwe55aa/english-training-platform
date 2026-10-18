import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from courses.models import Course, Lesson, Session, Student, default_student_id

TITLES=['Welcome!',"Hello, I'm Anna!","I'm Here!",'What Is It?','Where Are You?','Where Is the Gym?','What Are You Doing?','Are You Busy?','Is It Cold?','Come Over to My Place','This Is My Neighborhood','Meet My Family']

class Command(BaseCommand):
    help='Initialize the current course without overwriting teacher edits.'
    @transaction.atomic
    def handle(self,*args,**options):
        course,course_created=Course.objects.get_or_create(order=1,defaults={'title':"VOA · Let's Learn English Level 1",'published':True})
        student=Student.objects.get(pk=default_student_id())
        if course_created:student.courses.add(course)
        data=json.loads(Path(__file__).resolve().parents[2].joinpath('data/sessions.json').read_text())
        urls={2*i+j+1:url for i,s in enumerate(data) for j,url in enumerate(s['urls'])}
        lessons={}
        for number in range(1,53):
            lesson,_=Lesson.objects.get_or_create(course=course,number=number,defaults={'title':TITLES[number-1] if number<=12 else f'Lesson {number}', 'source_url':urls.get(number,''),'published':number<=12})
            lessons[number]=lesson
        for item in data:
            number=item['number']
            values={k:v for k,v in item.items() if k not in ['number','urls']}
            session,created=Session.objects.get_or_create(student=student,number=number,defaults={**values,'published':True})
            if created: session.lessons.set([lessons[number*2-1],lessons[number*2]])
        self.stdout.write('Course ready; existing teacher edits preserved.')
