from django.test import TestCase
from django.core.exceptions import ValidationError
from courses.models import Course, Lesson, Session, MasteryRecord, Recording

class CourseModelsTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title='VOA Level 1')
    def test_unique_lesson_numbers(self):
        Lesson.objects.create(course=self.course, number=1, title='Hello')
        duplicate = Lesson(course=self.course, number=1, title='Duplicate')
        with self.assertRaises(ValidationError): duplicate.full_clean()
    def test_prepared_does_not_count_completed(self):
        Session.objects.create(number=1, title='Done', status='completed')
        Session.objects.create(number=2, title='Next', status='prepared')
        self.assertEqual(Session.objects.filter(status='completed').count(), 1)
    def test_invalid_mastery_rejected(self):
        session = Session.objects.create(number=1, title='Test')
        record = MasteryRecord(session=session, task='say hello', state='fluent')
        with self.assertRaises(ValidationError): record.full_clean()
    def test_drafts_hidden_by_default(self):
        self.assertFalse(Lesson(course=self.course, number=1).published)
        self.assertFalse(Session(number=1).published)
        self.assertFalse(Recording().published)
    def test_public_recording_requires_consent(self):
        record = Recording(title='test', published=True, file='recordings/test.mp4')
        with self.assertRaises(ValidationError): record.full_clean()
