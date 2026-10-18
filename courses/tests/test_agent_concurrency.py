"""Exercise separate SQLite connections without touching the configured database."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase


class AgentSQLiteConcurrencyTests(TestCase):
    def test_duplicate_retries_and_revision_conflicts(self):
        script = r'''
import os, threading
from concurrent.futures import ThreadPoolExecutor
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.core.management import call_command
from django.db import connections
from courses.agent.service import execute
from courses.models import AgentOperation, RewardEntry, Student
call_command('migrate', verbosity=0)
student = Student.objects.get(slug='learner')
request = {'tool': 'rewards.award', 'arguments': {'student_id': student.pk,
    'date': '2026-10-18', 'title': 'Concurrency test', 'amount': 10,
    'evidence': 'Isolated test observation'}, 'request_id': 'duplicate', 'apply': True}
barrier = threading.Barrier(4)
def worker(request):
    try:
        barrier.wait(timeout=10)
        return execute(request)
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(worker, [request] * 4))
assert all(r['ok'] or r['error']['code'] == 'conflict' for r in results), results
assert RewardEntry.objects.count() == 1
assert AgentOperation.objects.filter(request_id='duplicate').count() == 1
for _ in results:
    assert execute(request).get('replayed') is True
revision = execute({'tool': 'students.get', 'arguments': {
    'student_id': student.pk}})['result']['student']['revision']
requests = [{'tool': 'students.save', 'arguments': {'student_id': student.pk,
    'expected_revision': revision, 'fields': {'goal': goal}},
    'request_id': goal, 'apply': True} for goal in ['first', 'second']]
barrier = threading.Barrier(2)
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(worker, requests))
assert sum(r['ok'] for r in results) == 1, results
assert all(r['ok'] or r['error']['code'] in ('conflict', 'stale_revision')
           for r in results), results
for request, result in zip(requests, results):
    if not result['ok']:
        assert execute(request)['error']['code'] == 'stale_revision'
assert AgentOperation.objects.count() == 2
'''
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, 'SECRET_KEY': 'isolated-concurrency-test',
                           'DATABASE_PATH': str(Path(directory) / 'test.sqlite3')}
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=Path(__file__).resolve().parents[2], env=environment,
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
