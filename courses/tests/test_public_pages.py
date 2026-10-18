from django.test import TestCase
from courses.models import Course, Lesson, Session

class PublicPagesTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title='VOA', published=True)
        from courses.models import Student
        Student.objects.get(slug='learner').courses.add(self.course)
        self.lesson = Lesson.objects.create(course=self.course, number=1, title='Welcome', published=True)
        self.done = Session.objects.create(number=1, title='公开课堂', status='completed', published=True, teacher_reflection='teacher-secret')
        self.done.lessons.add(self.lesson)
        self.next = Session.objects.create(number=2, title='下一课', status='prepared', published=True)
        self.draft = Session.objects.create(number=3, title='secret-draft')
    def test_home_anonymous_progress(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['completed_sessions'], 1)
        self.assertEqual(r.context['completed_lessons'], 1)
        self.assertContains(r, '168')
        self.assertContains(r, '52')
        self.assertNotContains(r, 'secret-draft')
    def test_draft_unavailable(self):
        self.assertEqual(self.client.get(f'/sessions/{self.draft.pk}/').status_code, 404)
    def test_public_session_hides_teacher_evidence(self):
        r = self.client.get(f'/sessions/{self.done.pk}/')
        self.assertContains(r, '公开课堂')
        self.assertNotContains(r, 'teacher-secret')
    def test_public_views_reject_post(self):
        for path in ['/', '/lessons/', '/progress/', f'/sessions/{self.done.pk}/']:
            self.assertEqual(self.client.post(path, {'status':'completed'}).status_code, 405)
        self.next.refresh_from_db()
        self.assertEqual(self.next.status, 'prepared')
    def test_accessible_states(self):
        r = self.client.get('/')
        self.assertContains(r, '已完成')
        self.assertContains(r, '当前课堂')
        self.assertContains(r, 'viewport')
    def test_unpublished_course_does_not_expose_materials(self):
        self.lesson.title='withdrawn-lesson-title';self.lesson.source_url='https://example.com/withdrawn-material';self.lesson.save()
        self.course.published=False;self.course.save()
        for url in ['/', '/lessons/', f'/sessions/{self.done.pk}/']:
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertNotContains(response,'withdrawn-material')
            self.assertNotContains(response,'withdrawn-lesson-title')
    def test_read_only_pages_support_head_requests(self):
        for url in ['/', '/lessons/', '/progress/', '/recordings/', f'/sessions/{self.done.pk}/', '/health/']:
            response=self.client.head(url)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.content,b'')
