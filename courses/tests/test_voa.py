import json
import tempfile
from pathlib import Path
from django.test import TestCase, SimpleTestCase, override_settings
from courses.models import Course, Lesson

class ParserTests(SimpleTestCase):
    def test_extracts_conversation_only_and_all_video_roles(self):
        from courses.voa import parse_lesson
        html='''<h1>Lesson 11: Neighborhood</h1><video title="Main" src="https://voa-video-ns.akamaized.net/main.mp4"></video><div class="wsw"><h2>Speaking Practice</h2><video title="Speaking" src="https://voa-video-ns.akamaized.net/speak.mp4"></video><h2>Conversation</h2><div>Anna: Hello! <strong>Nice</strong> day.</div><div>Marsha: Yes.</div><h2>Listening Quiz</h2><a data-ajax-url="/Quiz/Start?id=123&page=1">Start</a></div>'''
        data=parse_lesson(html)
        self.assertEqual(data['transcript'],['Anna: Hello! Nice day.','Marsha: Yes.'])
        self.assertEqual(len(data['videos']),2)
        self.assertEqual(data['quiz_id'],'123')

    def test_quiz_uses_official_correct_marker_and_explanation(self):
        from courses.voa import parse_quiz
        html='''<span class="caption">Question 1 / 2</span><h2 class="quiz__question-title">Where?</h2><li class="quiz__answers-item quiz__answers-item--false"><span class="quiz__answers-item-text">Here</span></li><li class="quiz__answers-item quiz__answers-item--correct"><span class="quiz__answers-item-text">There</span></li><form><p class="clear">She says there.</p></form>'''
        q,total=parse_quiz(html)
        self.assertEqual(total,2)
        self.assertEqual(q['answer'],1)
        self.assertEqual(q['explanation'],'She says there.')
        self.assertEqual(q['options'],['Here','There'])

    def test_rejects_untrusted_network_urls(self):
        from courses.voa import validate_url
        for url in ['http://learningenglish.voanews.com/a/x','https://localhost/a','https://voanews.com.evil.test/a','https://user:password@learningenglish.voanews.com/a']:
            with self.assertRaises(ValueError): validate_url(url)

class MaterialTests(TestCase):
    def setUp(self):
        from courses.models import LessonMaterial
        c=Course.objects.create(title='VOA',published=True)
        from courses.models import Student
        Student.objects.get(slug='jason').courses.add(c)
        self.lesson=Lesson.objects.create(course=c,number=1,title='Hello',published=True)
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.temp.name);self.override.enable();self.addCleanup(self.override.disable)
        path=Path(self.temp.name)/'voa/lesson-01/test.mp4';path.parent.mkdir(parents=True);path.write_bytes(b'video')
        self.material=LessonMaterial.objects.create(lesson=self.lesson,published=True,data={'transcript':['Anna: <script>alert(1)</script>'],'videos':['main'],'quiz':[{'question':'Where?','options':['Here','There'],'answer':1,'media':[]}],'assets':{'main':{'file':'voa/lesson-01/test.mp4','title':'Main'}}})

    def test_public_material_renders_safe_text_and_local_video(self):
        r=self.client.get(f'/materials/{self.lesson.pk}/')
        self.assertContains(r,'&lt;script&gt;')
        self.assertContains(r,f'/materials/{self.lesson.pk}/media/main/')
        self.assertContains(r,'Where?')
        self.assertNotContains(r,'<script>alert(1)</script>')

    def test_unpublishing_course_or_material_revokes_both_routes(self):
        urls=[f'/materials/{self.lesson.pk}/',f'/materials/{self.lesson.pk}/media/main/']
        self.assertEqual(self.client.get(urls[1])['X-Accel-Redirect'],'/_protected_media/voa/lesson-01/test.mp4')
        for obj in [self.material,self.lesson,self.lesson.course]:
            obj.published=False;obj.save()
            for url in urls:self.assertEqual(self.client.get(url).status_code,404)
            obj.published=True;obj.save()

    def test_media_traversal_and_missing_files_are_not_served(self):
        for name in ['../private.mp4','recordings/private.mp4','voa/missing.mp4']:
            self.material.data['assets']['main']['file']=name;self.material.save()
            self.assertEqual(self.client.get(f'/materials/{self.lesson.pk}/media/main/').status_code,404)

class TranscriptLayoutTests(SimpleTestCase):
    def test_nested_paragraphs_and_breaks_preserve_speaker_lines(self):
        from courses.voa import parse_lesson
        d=parse_lesson('<div class="wsw"><h2>Conversation</h2><div><p>Anna: Hello.<br>Marsha: Hi <b>Anna</b>.</p><p>Anna: Bye.</p></div><h2>Quiz</h2></div>')
        self.assertEqual(d['transcript'],['Anna: Hello.','Marsha: Hi Anna.','Anna: Bye.'])

class OfflineImportTests(TestCase):
    def test_verified_archive_import_is_repeatable_and_keeps_teacher_progress(self):
        import hashlib
        from django.core.management import call_command
        from courses.models import Session, LessonMaterial
        from io import StringIO
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'archive';media=root/'media'
            source=archive/'media/lesson-01/test.mp4';source.parent.mkdir(parents=True);source.write_bytes(b'known-content')
            course=Course.objects.create(title='VOA',published=True)
            lesson=Lesson.objects.create(course=course,number=1,title='Teacher title',source_url='https://learningenglish.voanews.com/a/lesson/123.html',published=True)
            session=Session.objects.create(number=1,title='Class',status='completed',teacher_reflection='Private notes')
            data={'number':1,'title':'VOA title','source_url':lesson.source_url,'fetched_at':'2026-10-18','transcript':['Anna: Hello'],'videos':['main'],'quiz':[],'assets':{'main':{'file':'voa/lesson-01/test.mp4','title':'Main','quality':'360p','bytes':13,'sha256':hashlib.sha256(b'known-content').hexdigest()}}}
            (archive/'lesson-01.json').write_text(json.dumps(data))
            with override_settings(MEDIA_ROOT=str(media)):
                for _ in range(2):call_command('import_voa',start=1,end=1,archive=str(archive),offline=True,publish=True,document=str(root/'doc.md'),stdout=StringIO())
                self.assertEqual(LessonMaterial.objects.count(),1)
                self.assertEqual(next((media/'voa/lesson-01').glob('*.mp4')).read_bytes(),b'known-content')
                source.write_bytes(b'corrupt')
                from django.core.management.base import CommandError
                with self.assertRaises(CommandError):call_command('import_voa',start=1,end=1,archive=str(archive),offline=True,publish=True,document=str(root/'doc.md'),stdout=StringIO(),stderr=StringIO())
            session.refresh_from_db();lesson.refresh_from_db()
            self.assertEqual(session.status,'completed')
            self.assertEqual(session.teacher_reflection,'Private notes')
            self.assertEqual(lesson.title,'Teacher title')

class MediaValidationTests(SimpleTestCase):
    def test_real_mp4_is_playable_but_html_in_mp4_is_rejected(self):
        from courses.voa import validate_video
        valid=Path(__file__).parent/'fixtures/sample.mp4'
        info=validate_video(valid)
        self.assertGreater(info['duration'],0)
        with tempfile.TemporaryDirectory() as temp:
            invalid=Path(temp)/'error.mp4';invalid.write_text('<html>error</html>')
            with self.assertRaises(ValueError):validate_video(invalid)

class AtomicImportTests(TestCase):
    def test_failed_later_file_keeps_existing_published_media(self):
        import hashlib
        from io import StringIO
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from courses.models import LessonMaterial
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'archive';target=root/'site'
            c=Course.objects.create(title='VOA',published=True)
            l=Lesson.objects.create(course=c,number=1,title='One',source_url='https://learningenglish.voanews.com/a/1.html',published=True)
            assets={}
            for filename,content in [('one.mp4',b'NEW'),('two.mp4',b'BAD')]:
                p=archive/'media/lesson-01'/filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
                assets[filename]={'file':'voa/lesson-01/'+filename,'bytes':3,'sha256':hashlib.sha256(b'NEW').hexdigest()}
            old=target/'voa/lesson-01/one.mp4';old.parent.mkdir(parents=True);old.write_bytes(b'OLD')
            LessonMaterial.objects.create(lesson=l,published=True,data={'old':True})
            (archive/'lesson-01.json').write_text(json.dumps({'number':1,'source_url':l.source_url,'assets':assets}))
            with override_settings(MEDIA_ROOT=str(target)):
                with self.assertRaises(CommandError):call_command('import_voa',start=1,end=1,archive=str(archive),offline=True,document=str(root/'out.md'),stdout=StringIO(),stderr=StringIO())
            self.assertEqual(old.read_bytes(),b'OLD')
            self.assertEqual(LessonMaterial.objects.get(lesson=l).data,{'old':True})

class ArchiveIntegrityTests(SimpleTestCase):
    def test_existing_manifest_does_not_silently_rebaseline_changed_cache(self):
        import hashlib,shutil
        from courses.voa import archive_lesson
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'raw').mkdir();(root/'media/lesson-01').mkdir(parents=True)
            url='https://voa-video-ns.akamaized.net/test.mp4'
            key=hashlib.sha256(url.encode()).hexdigest()[:20]
            (root/'raw/lesson-01.html').write_text(f'<h1>Lesson 1</h1><video src="{url}"></video><div class="wsw"><h2>Conversation</h2><p>Anna: Hi.</p></div>')
            shutil.copy2(Path(__file__).parent/'fixtures/sample.mp4',root/'media/lesson-01'/f'{key}.mp4')
            old={'assets':{key:{'url':url,'sha256':'0'*64}}}
            (root/'lesson-01.json').write_text(json.dumps(old))
            with self.assertRaises(ValueError):archive_lesson(1,'https://learningenglish.voanews.com/a/1.html',root)
            self.assertEqual(json.loads((root/'lesson-01.json').read_text()),old)
