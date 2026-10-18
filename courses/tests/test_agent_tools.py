from django.test import TestCase
from courses.models import Student

class AgentToolsTests(TestCase):
    def call(self,tool,args=None,**kw):
        from courses.agent.service import execute
        return execute({'tool':tool,'arguments':args or {},**kw})
    def test_discovery_and_teacher_context(self):
        tools=self.call('tools.list')
        self.assertTrue(tools['ok']);self.assertIn('students.save',[t['name'] for t in tools['result']['tools']])
        result=self.call('students.get',{'student_id':Student.objects.get(slug='learner').pk})
        self.assertEqual(result['result']['student']['slug'],'learner');self.assertIn('revision',result['result']['student'])
    def test_preview_has_no_side_effect_and_apply_replay_is_once(self):
        count=Student.objects.count();args={'fields':{'name':'Lily','planned_sessions':12}}
        preview=self.call('students.save',args,request_id='test-create')
        self.assertTrue(preview['ok']);self.assertTrue(preview['dry_run']);self.assertEqual(Student.objects.count(),count)
        first=self.call('students.save',args,request_id='test-create',apply=True)
        again=self.call('students.save',args,request_id='test-create',apply=True)
        self.assertEqual(first['result'],again['result']);self.assertTrue(again['replayed']);self.assertEqual(Student.objects.count(),count+1)
        other=self.call('students.save',{'fields':{'name':'Different'}},request_id='test-create',apply=True)
        self.assertEqual(other['error']['code'],'idempotency_conflict')
    def test_revision_and_unknown_field_guard(self):
        s=Student.objects.get(slug='learner');snapshot=self.call('students.get',{'student_id':s.pk})['result']['student']
        args={'student_id':s.pk,'expected_revision':snapshot['revision'],'fields':{'goal':'Talk at work'}}
        self.assertTrue(self.call('students.save',args,request_id='update',apply=True)['ok'])
        self.assertEqual(self.call('students.save',args,request_id='stale',apply=True)['error']['code'],'stale_revision')
        self.assertFalse(self.call('students.save',{'fields':{'name':'Bad','is_superuser':True}},request_id='unknown',apply=True)['ok'])
    def test_write_requires_request_id_and_apply_boolean(self):
        self.assertFalse(self.call('students.save',{'fields':{'name':'bad'}},apply=True)['ok'])
        self.assertFalse(self.call('students.save',{'fields':{'name':'bad'}},request_id='bad',apply='false')['ok'])
    def course_lesson(self):
        from courses.models import Course,Lesson
        course=Course.objects.create(title='Book',published=True)
        lesson=Lesson.objects.create(course=course,number=1,title='Hello',published=True)
        Student.objects.get(slug='learner').courses.add(course)
        return course,lesson
    def test_material_preview_and_atomic_append_keeps_legacy(self):
        from courses.models import ContentBlock,LessonMaterial
        course,lesson=self.course_lesson()
        LessonMaterial.objects.create(lesson=lesson,data={'transcript':['Original']},published=True)
        current=self.call('materials.get',{'lesson_id':lesson.pk})['result']['material']
        args={'lesson_id':lesson.pk,'expected_revision':current['revision'],'fields':{'title':'Hello'},'blocks':[{'title':'Script','kind':'text','text':'Hello, Learner!','published':True}]}
        self.assertTrue(self.call('materials.import',args,request_id='preview')['ok']);self.assertEqual(ContentBlock.objects.count(),0)
        applied=self.call('materials.import',args,request_id='import',apply=True);self.assertTrue(applied['ok'],applied)
        self.assertEqual(LessonMaterial.objects.get().data['transcript'],['Original'])
        self.assertEqual(self.call('materials.import',args,request_id='stale-import',apply=True)['error']['code'],'stale_revision')
        bad={'course_id':course.pk,'fields':{'number':2,'title':'Bad'},'blocks':[{'title':'Valid','kind':'text','text':'Hello'},{'title':'Invalid','kind':'quiz','question':'Who?','options':['A'],'correct_choice':3}]}
        self.assertFalse(self.call('materials.import',bad,request_id='bad-import',apply=True)['ok']);self.assertEqual(ContentBlock.objects.count(),1)
    def test_prepare_progress_award_and_context(self):
        from courses.models import Session,RewardEntry,MasteryRecord
        course,lesson=self.course_lesson();student=Student.objects.get(slug='learner')
        args={'student_id':student.pk,'number':2,'lesson_ids':[lesson.pk],'fields':{'title':'Meet friends','goal':'Introduce yourself','review_sentences':['Hello','My name is Learner','Nice to meet you','Where are you from?','I am from Liaoning'],'expressions':[{'en':'Hello','zh':'你好'}],'activities':[{'title':'Review','minutes':10,'instruction':'Recall yesterday'},{'title':'Learn','minutes':20,'instruction':'Listen and speak'},{'title':'Practice','minutes':25,'instruction':'Role play'},{'title':'Exit','minutes':5,'instruction':'Summarize'}],'b_plan':'Model one line at a time','exit_check':'Introduce yourself without prompts'}}
        prepared=self.call('sessions.prepare',args,request_id='prepare',apply=True)
        self.assertTrue(prepared['ok'],prepared);session=prepared['result']['session'];self.assertEqual(session['status'],'prepared')
        invalid=self.call('sessions.progress',{'session_id':session['id'],'expected_revision':session['revision'],'status':'completed','date':'2026-10-18','evidence':''},request_id='invalid',apply=True)
        self.assertFalse(invalid['ok']);self.assertEqual(Session.objects.get(pk=session['id']).status,'prepared')
        done=self.call('sessions.progress',{'session_id':session['id'],'expected_revision':session['revision'],'status':'completed','date':'2026-10-18','evidence':'Teacher confirmed class completed','mastery':[{'task':'Introduce himself','state':'prompted','evidence':'Needed one prompt'}]},request_id='done',apply=True)
        self.assertTrue(done['ok'],done);self.assertEqual(MasteryRecord.objects.count(),1)
        reward={'student_id':student.pk,'amount':10,'date':'2026-10-18','title':'主动练习','evidence':'Teacher observed one full dialogue'}
        first=self.call('rewards.award',reward,request_id='reward',apply=True)
        self.assertTrue(first['ok'],first);self.call('rewards.award',reward,request_id='reward',apply=True);self.assertEqual(RewardEntry.objects.count(),1)
        context=self.call('students.get',{'student_id':student.pk})['result'];self.assertEqual(context['progress']['completed_sessions'],0) # draft class is not public
        self.assertEqual(context['recorded_progress']['completed_sessions'],1)
    def test_prepare_rejects_incomplete_template_and_unassigned_lesson(self):
        course,lesson=self.course_lesson()
        args={'student_id':Student.objects.get(slug='learner').pk,'number':2,'lesson_ids':[lesson.pk],'fields':{'title':'Too little'}}
        self.assertFalse(self.call('sessions.prepare',args,request_id='incomplete',apply=True)['ok'])
        from courses.models import Session
        self.assertFalse(Session.objects.exists())
    def test_audit_admin_is_read_only_and_private(self):
        from django.contrib.auth import get_user_model
        from courses.models import AgentOperation
        self.call('students.save',{'fields':{'name':'Audit'}},request_id='audit',apply=True)
        op=AgentOperation.objects.get(request_id='audit')
        self.assertEqual(self.client.get('/admin/courses/agentoperation/').status_code,302)
        user=get_user_model().objects.create_superuser('teacher','','test-password')
        self.client.force_login(user)
        self.assertEqual(self.client.get(f'/admin/courses/agentoperation/{op.pk}/change/').status_code,200)
        for path in ['add/',f'{op.pk}/delete/',f'{op.pk}/change/']:
            self.assertEqual(self.client.post('/admin/courses/agentoperation/'+path,{}).status_code,403)
    def test_management_command_json_and_size_error(self):
        from django.core.management import call_command
        from io import StringIO
        import json
        out=StringIO();call_command('agent_tool',stdin=StringIO('{"tool":"students.list"}'),stdout=out)
        self.assertTrue(json.loads(out.getvalue())['ok'])
        out=StringIO();call_command('agent_tool',stdin=StringIO('{bad json'),stdout=out)
        self.assertEqual(json.loads(out.getvalue())['error']['code'],'invalid_json')
    def test_quiz_option_newline_cannot_change_answer_mapping(self):
        from courses.models import ContentBlock
        course,_=self.course_lesson()
        result=self.call('materials.import',{'course_id':course.pk,'fields':{'number':2,'title':'Quiz'},'blocks':[{'kind':'quiz','title':'Quiz','question':'Q?','options':['A\nB','C'],'correct_choice':2}]},request_id='multiline-options',apply=True)
        self.assertFalse(result['ok']);self.assertFalse(ContentBlock.objects.exists())
    def test_whitespace_template_and_empty_expressions_are_rejected(self):
        from courses.models import Session
        _,lesson=self.course_lesson()
        fields={'title':'  ','goal':'  ','b_plan':'  ','exit_check':'  ','expressions':[{'en':'','zh':''}],'activities':[{'title':'Practice','minutes':60,'instruction':'Speak'}]}
        args={'student_id':Student.objects.get(slug='learner').pk,'number':1,'lesson_ids':[lesson.pk],'fields':fields}
        self.assertFalse(self.call('sessions.prepare',args,request_id='blank-template',apply=True)['ok'])
        fields.update(title='Title',goal='Goal',b_plan='Repeat once',exit_check='Say hello')
        self.assertFalse(self.call('sessions.prepare',args,request_id='blank-expressions',apply=True)['ok'])
        self.assertFalse(Session.objects.exists())
    def test_quiz_options_reject_all_splitlines_boundaries_and_blank_items(self):
        from courses.models import ContentBlock
        course,_=self.course_lesson()
        values=['','   ']+['A'+separator+'B' for separator in ['\n','\r','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029']]
        for index,value in enumerate(values):
            with self.subTest(option=repr(value)):
                result=self.call('materials.import',{'course_id':course.pk,'fields':{'number':index+2,'title':'Quiz'},'blocks':[{'kind':'quiz','title':'Quiz','question':'Q?','options':['A',value,'C'],'correct_choice':2}]},request_id=f'split-option-{index}',apply=True)
                self.assertFalse(result['ok'])
        self.assertFalse(ContentBlock.objects.exists())
    def test_generic_agent_material_does_not_show_unrelated_voa_backup(self):
        from courses.models import Session
        _,lesson=self.course_lesson()
        session=Session.objects.create(number=1,title='Book class',published=True);session.lessons.add(lesson)
        response=self.client.get(f'/sessions/{session.pk}/')
        self.assertNotContains(response,'BV1wHPLeUE8r')
        lesson.source_url='https://learningenglish.voanews.com/a/test/1.html';lesson.save()
        response=self.client.get(f'/sessions/{session.pk}/');self.assertContains(response,'BV1wHPLeUE8r')
