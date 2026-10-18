from io import BytesIO
from pathlib import Path
import tempfile
from django.test import TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from courses.models import Student,Course,ContentBlock,Lesson,AgentOperation
from courses.agent.service import execute
from courses.agent.uploads import stage,open_upload
from courses.agent.schema import ToolError

class AgentUploadTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.settings=override_settings(MEDIA_ROOT=root/'media',AGENT_UPLOAD_ROOT=root/'staging');self.settings.enable();self.addCleanup(self.settings.disable)
        self.root=root;self.course=Course.objects.create(title='Files')
        self.video=(Path(__file__).parent/'fixtures/sample.mp4').read_bytes()
    def request(self,blocks,apply=False):
        return execute({'tool':'materials.import','arguments':{'course_id':self.course.pk,'fields':{'number':1,'title':'Files'},'blocks':blocks},'request_id':'file-import','apply':apply})
    def test_staging_traversal_and_truncated_stream_rejected(self):
        with self.assertRaises(ToolError):open_upload('../db.sqlite3')
        with self.assertRaises(ToolError):stage(BytesIO(b'x'),'test.mp4',4)
        self.assertEqual(list((self.root/'staging').glob('*')),[])
    def test_preview_validates_file_but_persists_nothing_then_apply_consumes(self):
        handle=stage(BytesIO(self.video),'video.mp4',len(self.video))['upload_handle']
        blocks=[{'title':'Video','kind':'video','upload_handle':handle}]
        preview=self.request(blocks);self.assertTrue(preview['ok'],preview)
        self.assertFalse(ContentBlock.objects.exists());self.assertFalse(Lesson.objects.exists());self.assertFalse(AgentOperation.objects.exists())
        self.assertEqual(list((self.root/'media').rglob('*.mp4')),[])
        self.assertTrue((self.root/'staging'/handle).exists())
        result=self.request(blocks,True);self.assertTrue(result['ok'],result)
        self.assertFalse((self.root/'staging'/handle).exists());self.assertEqual(ContentBlock.objects.count(),1)
        block=ContentBlock.objects.get();self.assertEqual(Path(block.file.path).read_bytes(),self.video)
        self.assertTrue(self.request(blocks,True)['replayed'])
    def test_failed_later_block_rolls_back_media_and_database(self):
        handle=stage(BytesIO(self.video),'video.mp4',len(self.video))['upload_handle']
        result=self.request([{'title':'Video','kind':'video','upload_handle':handle},{'title':'Broken','kind':'document','upload_handle':'0'*32+'.pdf'}],True)
        self.assertFalse(result['ok']);self.assertFalse(ContentBlock.objects.exists());self.assertFalse(Lesson.objects.exists());self.assertFalse(AgentOperation.objects.exists())
        self.assertEqual(list((self.root/'media').rglob('*.mp4')),[]);self.assertTrue((self.root/'staging'/handle).exists())
