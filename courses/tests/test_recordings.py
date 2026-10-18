import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from courses.models import Recording
from courses.forms import RecordingAdminForm

class RecordingTest(TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.setting=override_settings(MEDIA_ROOT=self.directory.name)
        self.setting.enable()
        self.addCleanup(self.setting.disable)
        self.addCleanup(self.directory.cleanup)
    def form(self, name='test.mp4', data=None, consent=True, published=True):
        data=data if data is not None else Path(__file__).with_name('fixtures').joinpath('sample.mp4').read_bytes()
        return RecordingAdminForm(data={'student':__import__('courses.models',fromlist=['default_student_id']).default_student_id(),'title':'Test','duration':0,'published':published,'consent_confirmed':consent}, files={'file':SimpleUploadedFile(name,data,content_type='video/mp4')})
    def test_valid_mp4(self):
        form=self.form()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertGreaterEqual(form.save().duration,1)
    def test_forged_file_rejected(self):
        form=self.form(data=b'0000ftyp'+b'bad'*100)
        self.assertFalse(form.is_valid())
        self.assertIn('file',form.errors)
    def test_wrong_extension_rejected(self):
        self.assertFalse(self.form(name='evil.html').is_valid())
    def test_consent_required(self):
        form=self.form(consent=False)
        self.assertFalse(form.is_valid())
        self.assertIn('consent_confirmed',form.errors)
    def test_unpublished_media_hidden_even_known_url(self):
        record=self.form(published=False).save()
        for url in [f'/recordings/{record.pk}/',f'/recordings/{record.pk}/stream/','/media/'+record.file.name]:
            self.assertEqual(self.client.get(url).status_code,404)
    def test_published_stream_uses_internal_redirect(self):
        record=self.form().save()
        r=self.client.get(f'/recordings/{record.pk}/stream/',HTTP_RANGE='bytes=0-99')
        self.assertEqual(r.status_code,200)
        self.assertTrue(r['X-Accel-Redirect'].startswith('/_protected_media/recordings/'))
        record.published=False;record.save()
        self.assertEqual(self.client.get(f'/recordings/{record.pk}/stream/').status_code,404)
    def test_anonymous_upload_rejected(self):
        r=self.client.post('/admin/courses/recording/add/',{'title':'test'})
        self.assertEqual(r.status_code,302)
        self.assertEqual(Recording.objects.count(),0)
    def test_undecodable_payload_rejected(self):
        data=bytearray(Path(__file__).with_name('fixtures').joinpath('sample.mp4').read_bytes())
        offset=data.index(b'mdat')+4
        data[offset:]=b'\x00'*(len(data)-offset)
        form=self.form(data=bytes(data))
        self.assertFalse(form.is_valid())
        self.assertIn('file',form.errors)
