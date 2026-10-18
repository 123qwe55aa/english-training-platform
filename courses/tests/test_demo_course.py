from django.test import TestCase
from django.core.management import call_command
from courses.models import Course, Lesson, Session, Badge
import json
from pathlib import Path

class DemoTest(TestCase):
    def test_seed_idempotent_and_prepared_not_complete(self):
        call_command('seed_demo_course', verbosity=0)
        call_command('seed_demo_course', verbosity=0)
        self.assertEqual(Course.objects.count(),1)
        self.assertEqual(Lesson.objects.count(),52)
        self.assertEqual(Session.objects.count(),6)
        self.assertEqual(Session.objects.filter(status='completed').count(),0)
        self.assertEqual(Session.objects.get(number=6).status,'prepared')
        self.assertEqual(Badge.objects.count(),0)

    def test_public_seed_contains_no_real_learner_progress(self):
        data=json.loads(Path(__file__).resolve().parents[1].joinpath('data/sessions.json').read_text())
        self.assertTrue(data)
        self.assertTrue(all(item['status']=='prepared' and item['date'] is None for item in data))
        encoded=json.dumps(data,ensure_ascii=False).lower()
        self.assertNotIn('jason',encoded)
        self.assertNotIn('liaoning',encoded)
    def test_reseeding_preserves_teacher_edits(self):
        call_command('seed_demo_course',verbosity=0)
        session=Session.objects.get(number=6)
        session.title='Teacher updated';session.status='completed';session.save()
        call_command('seed_demo_course',verbosity=0)
        session.refresh_from_db()
        self.assertEqual(session.title,'Teacher updated')
        self.assertEqual(session.status,'completed')
