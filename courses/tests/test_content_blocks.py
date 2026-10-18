import tempfile
from pathlib import Path
from django.test import TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from courses.models import Course,Lesson,Student

class ContentTests(TestCase):
    def setUp(self):
        from courses.models import ContentBlock
        self.Block=ContentBlock
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.settings=override_settings(MEDIA_ROOT=self.temp.name);self.settings.enable();self.addCleanup(self.settings.disable)
        self.course=Course.objects.create(title='绘本',published=True)
        Student.objects.get(slug='jason').courses.add(self.course)
        self.lesson=Lesson.objects.create(course=self.course,number=100,title='A new book',published=True)
    def test_blocks_render_in_order_and_hide_drafts_and_html(self):
        self.Block.objects.create(lesson=self.lesson,kind='text',title='Second',text='<script>bad</script>',order=2,published=True)
        self.Block.objects.create(lesson=self.lesson,kind='dialogue',title='First',text='Hello!',order=1,published=True)
        self.Block.objects.create(lesson=self.lesson,kind='text',title='Draft-secret',text='secret')
        response=self.client.get(f'/materials/{self.lesson.pk}/');html=response.content.decode()
        self.assertLess(html.index('First'),html.index('Second'));self.assertContains(response,'&lt;script&gt;');self.assertNotContains(response,'Draft-secret')
    def test_upload_video_and_publication_gated_stream(self):
        from courses.forms import ContentBlockForm
        video=Path(__file__).parent/'fixtures/sample.mp4'
        form=ContentBlockForm(data={'lesson':self.lesson.pk,'title':'Video','kind':'video','order':1,'published':True},files={'file':SimpleUploadedFile('test.mp4',video.read_bytes(),content_type='video/mp4')})
        self.assertTrue(form.is_valid(),form.errors);block=form.save()
        url=f'/resources/{block.pk}/stream/'
        self.assertTrue(self.client.get(url)['X-Accel-Redirect'].startswith('/_protected_media/resources/'))
        for obj in [block,self.lesson,self.course]:
            obj.published=False;obj.save();self.assertEqual(self.client.get(url).status_code,404);obj.published=True;obj.save()
    def test_fake_pdf_and_invalid_quiz_are_rejected(self):
        from courses.forms import ContentBlockForm
        f=ContentBlockForm(data={'lesson':self.lesson.pk,'kind':'document','title':'Bad','order':1},files={'file':SimpleUploadedFile('bad.pdf',b'<script>alert(1)</script>')})
        self.assertFalse(f.is_valid())
        f=ContentBlockForm(data={'lesson':self.lesson.pk,'kind':'quiz','title':'Quiz','order':1,'question':'Q','option_lines':'One\nTwo','correct_choice':3})
        self.assertFalse(f.is_valid())
    def test_teacher_can_create_quiz_in_readable_admin_form(self):
        user=get_user_model().objects.create_superuser('teacher','','password-strong')
        self.client.force_login(user)
        r=self.client.post('/admin/courses/contentblock/add/',{'lesson':self.lesson.pk,'kind':'quiz','title':'Read','order':1,'question':'Who?','option_lines':'Anna\nPete','correct_choice':1,'published':'on','_save':'Save'})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.Block.objects.get().options,['Anna','Pete'])
    def test_pdf_requires_parseable_pages(self):
        from courses.forms import ContentBlockForm
        from pypdf import PdfWriter
        from io import BytesIO
        data={'lesson':self.lesson.pk,'kind':'document','title':'PDF','order':1,'published':True}
        broken=ContentBlockForm(data=data,files={'file':SimpleUploadedFile('broken.pdf',b'%PDF-1.7\nTHIS IS NOT A PDF')})
        self.assertFalse(broken.is_valid())
        writer=PdfWriter();writer.add_blank_page(width=300,height=400)
        buffer=BytesIO();writer.write(buffer)
        valid=ContentBlockForm(data=data,files={'file':SimpleUploadedFile('book.pdf',buffer.getvalue())})
        self.assertTrue(valid.is_valid(),valid.errors)
        block=valid.save()
        self.assertEqual(self.client.get(f'/resources/{block.pk}/stream/')['Content-Type'],'application/pdf')
