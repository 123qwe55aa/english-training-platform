import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

class PreservationMigrationTest(TestCase):
    def test_legacy_records_keep_ids_files_status_and_private_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={**os.environ,'DATABASE_PATH':str(Path(tmp)/'legacy.sqlite3'),'SECRET_KEY':'isolated-migration-test'}
            def run(*args):
                p=subprocess.run([sys.executable,'manage.py',*args],env=env,capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
            run('migrate','courses','0002','--noinput')
            run('shell','-c',"from django.db import connection; from django.db.migrations.executor import MigrationExecutor; a=MigrationExecutor(connection).loader.project_state([('courses','0002_lessonmaterial')]).apps; C=a.get_model('courses','Course'); L=a.get_model('courses','Lesson'); S=a.get_model('courses','Session'); M=a.get_model('courses','LessonMaterial'); B=a.get_model('courses','Badge'); R=a.get_model('courses','Recording'); c=C.objects.create(title='Original',published=True); l=L.objects.create(course=c,number=1,title='Original lesson',published=True); s=S.objects.create(number=1,title='Original class',status='completed',published=True,teacher_reflection='private evidence'); s.lessons.add(l); M.objects.create(lesson=l,data={'assets':{'main':{'file':'voa/lesson-01/original.mp4'}}},published=True); B.objects.create(name='Original badge',description='Preserve'); R.objects.create(title='Original recording',session=s,file='recordings/original.mp4')")
            run('migrate','--noinput')
            run('shell','-c',"from courses.models import *; j=Student.objects.get(slug='learner'); s=Session.objects.get(pk=1); assert s.student_id==j.pk and s.status=='completed' and s.teacher_reflection=='private evidence'; assert list(s.lessons.values_list('pk',flat=True))==[1]; assert LessonMaterial.objects.get(lesson_id=1).data['assets']['main']['file']=='voa/lesson-01/original.mp4'; assert Badge.objects.get(pk=1).student_id==j.pk; assert Recording.objects.get(pk=1).file.name=='recordings/original.mp4'; assert j.courses.count()==1")
