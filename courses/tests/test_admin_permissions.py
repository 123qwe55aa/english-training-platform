from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from courses.models import Session

class AdminTest(TestCase):
    def setUp(self):
        self.session = Session.objects.create(number=1, title='Before')
        self.admin = get_user_model().objects.create_superuser('teacher', '', 'test-password-strong')
    def test_anonymous_cannot_edit(self):
        r=self.client.post(f'/admin/courses/session/{self.session.pk}/change/', {'title':'Hacked'})
        self.assertEqual(r.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, 'Before')
    def test_nonstaff_cannot_edit(self):
        user=get_user_model().objects.create_user('visitor', password='password123')
        self.client.force_login(user)
        r=self.client.get('/admin/courses/session/')
        self.assertEqual(r.status_code, 302)
    def test_teacher_edit_form_available(self):
        self.client.force_login(self.admin)
        r=self.client.get(f'/admin/courses/session/{self.session.pk}/change/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'teacher_reflection')
    def test_csrf_required(self):
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(f'/admin/courses/session/{self.session.pk}/change/', {}).status_code, 403)
    def test_teacher_can_save_readable_classroom_form(self):
        self.client.force_login(self.admin)
        response=self.client.post(f'/admin/courses/session/{self.session.pk}/change/', {'student':self.session.student_id,'number':1,'title':'Updated','status':'prepared','published':'on','expression_lines':'Hello. | 你好。','activity_lines':'开口练习 | 5 | 听一句，说一句 | 看图 | Hello.','mastery-TOTAL_FORMS':0,'mastery-INITIAL_FORMS':0,'mastery-MIN_NUM_FORMS':0,'mastery-MAX_NUM_FORMS':1000,'_save':'保存'})
        self.assertEqual(response.status_code,302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title,'Updated')
        self.assertEqual(self.session.expressions,[{'en':'Hello.','zh':'你好。'}])
