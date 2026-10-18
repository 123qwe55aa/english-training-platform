from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from courses.models import Course,Lesson,Session

class StudentTests(TestCase):
    def setUp(self):
        from courses.models import Student
        self.jason=Student.objects.get(slug='jason')
        self.other=Student.objects.create(name='Lily',slug='lily',published=True,planned_sessions=12,planned_lessons=4,daily_goal=60,video_points=5,dialogue_points=15)
        self.course=Course.objects.create(title='绘本',published=True)
        self.other.courses.add(self.course)
        self.lesson=Lesson.objects.create(course=self.course,number=60,title='Book',published=True)
        self.a=Session.objects.create(student=self.jason,number=1,title='Jason class',status='completed',published=True)
        self.b=Session.objects.create(student=self.other,number=1,title='Lily class',published=True)
        self.b.lessons.add(self.lesson)
    def test_profiles_have_independent_progress_and_legacy_root_stays_jason(self):
        r=self.client.get('/');self.assertEqual(r.context['completed_sessions'],1);self.assertNotContains(r,'Lily class')
        r=self.client.get('/s/lily/');self.assertEqual(r.context['completed_sessions'],0);self.assertEqual(r.context['planned_sessions'],12);self.assertContains(r,'Lily class');self.assertNotContains(r,'Jason class')
        self.assertContains(r,f'/s/lily/sessions/{self.b.pk}/')
    def test_detail_routes_cannot_mix_students(self):
        self.assertEqual(self.client.get(f'/sessions/{self.b.pk}/').status_code,404)
        self.assertEqual(self.client.get(f'/s/lily/sessions/{self.a.pk}/').status_code,404)
        self.assertEqual(self.client.get(f'/s/lily/materials/{self.lesson.pk}/').status_code,200)
        self.other.published=False;self.other.save();self.assertEqual(self.client.get('/s/lily/').status_code,404)
    def test_teacher_reward_and_config_are_per_student_and_read_only(self):
        from courses.models import RewardEntry
        RewardEntry.objects.create(student=self.other,date=timezone.localdate(),amount=25,title='主动开口')
        data=self.client.get('/s/lily/rewards/summary/').json()
        self.assertEqual(data['teacherPoints'],25);self.assertEqual(data['goal'],60);self.assertEqual(data['videoPoints'],5)
        self.assertEqual(self.client.get('/rewards/summary/').json()['teacherPoints'],0)
        self.assertEqual(self.client.post('/s/lily/rewards/summary/',{}).status_code,405)
    def test_session_number_only_unique_within_student(self):
        s=Session(student=self.other,number=1,title='duplicate')
        with self.assertRaises(ValidationError):s.full_clean()
    def test_removing_course_assignment_revokes_shared_material_for_that_student(self):
        self.other.courses.clear()
        self.assertEqual(self.client.get(f'/s/lily/materials/{self.lesson.pk}/').status_code,404)
        self.jason.courses.clear()
        self.assertEqual(self.client.get(f'/materials/{self.lesson.pk}/').status_code,404)
    def test_copy_plan_does_not_copy_scores_dates_or_private_reflection(self):
        from courses.student_services import copy_plan
        self.jason.courses.add(self.course);self.a.lessons.add(self.lesson)
        self.a.teacher_reflection='private';self.a.save()
        self.b.delete()
        self.assertEqual(copy_plan(self.jason,self.other),1)
        copied=self.other.sessions.get()
        self.assertEqual(copied.status,'planned');self.assertIsNone(copied.date);self.assertEqual(copied.teacher_reflection,'')
        copied.status='completed';copied.save()
        self.assertEqual(copy_plan(self.jason,self.other),0)
        copied.refresh_from_db();self.assertEqual(copied.status,'completed')
    def test_anonymous_cannot_create_student_progress_or_teacher_reward(self):
        from courses.models import RewardEntry,Student
        counts=(Student.objects.count(),Session.objects.count(),RewardEntry.objects.count())
        for kind in ['student','session','rewardentry','contentblock']:
            self.assertEqual(self.client.post(f'/admin/courses/{kind}/add/',{'name':'fake','amount':999}).status_code,302)
        self.assertEqual((Student.objects.count(),Session.objects.count(),RewardEntry.objects.count()),counts)
    def test_existing_session_cannot_change_student(self):
        self.a.student=self.other
        with self.assertRaisesMessage(ValidationError,'已有课堂不能更换学生'):
            self.a.full_clean()
    def test_admin_reassignment_keeps_session_and_recording_with_original_student(self):
        from django.contrib.auth import get_user_model
        from courses.models import Recording
        recording=Recording.objects.create(student=self.jason,session=self.a,title='Original replay',file='recordings/original.mp4',published=True,consent_confirmed=True)
        teacher=get_user_model().objects.create_superuser('review-teacher','','strong-review-password')
        self.client.force_login(teacher)
        response=self.client.post(f'/admin/courses/session/{self.a.pk}/change/',{
            'student':self.other.pk,'number':2,'title':'Other student title','status':'prepared','published':'on',
            'mastery-TOTAL_FORMS':0,'mastery-INITIAL_FORMS':0,'mastery-MIN_NUM_FORMS':0,'mastery-MAX_NUM_FORMS':1000,'_save':'Save',
        })
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'已有课堂不能更换学生')
        self.a.refresh_from_db();recording.refresh_from_db()
        self.assertEqual(self.a.student_id,self.jason.pk)
        self.assertEqual(self.a.title,'Jason class')
        self.assertEqual(self.a.status,'completed')
        self.assertEqual(recording.student_id,self.jason.pk)
        self.client.logout()
        response=self.client.get(f'/recordings/{recording.pk}/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Jason class')
        self.assertNotContains(response,'Other student title')
    def test_inconsistent_recording_ownership_is_hidden_from_public_routes(self):
        from courses.models import Recording
        recording=Recording.objects.create(student=self.jason,session=self.b,title='Inconsistent replay',file='recordings/inconsistent.mp4',published=True,consent_confirmed=True)
        self.assertNotContains(self.client.get('/recordings/'),'Inconsistent replay')
        for prefix in ['', '/s/lily']:
            for suffix in ['', 'stream/']:
                self.assertEqual(self.client.get(f'{prefix}/recordings/{recording.pk}/{suffix}').status_code,404)
    def test_lessons_title_contains_no_material_html(self):
        html=self.client.get('/s/lily/lessons/').content.decode()
        title=html.split('<title>')[1].split('</title>')[0]
        self.assertNotIn('<section',title)
        self.assertEqual(html.count('class="material-section"'),1)
