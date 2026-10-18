from django import forms
from .models import Session

class SessionAdminForm(forms.ModelForm):
    expression_lines = forms.CharField(label='重点表达', required=False, widget=forms.Textarea(attrs={'rows':8,'cols':85}), help_text='每行：英文句子 | 中文意思')
    activity_lines = forms.CharField(label='课堂流程', required=False, widget=forms.Textarea(attrs={'rows':12,'cols':85}), help_text='每行：步骤名称 | 分钟 | 老师带领方式 | 可选提示 | 学生输出任务')
    class Meta:
        model = Session
        exclude = ['expressions', 'activities']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['expression_lines'].initial = '\n'.join(f"{x.get('en','')} | {x.get('zh','')}" for x in self.instance.expressions)
            self.fields['activity_lines'].initial = '\n'.join(' | '.join(str(x.get(k,'')) for k in ['title','minutes','instruction','prompt','task']) for x in self.instance.activities)
    def clean_expression_lines(self):
        rows=[]
        for line in self.cleaned_data['expression_lines'].splitlines():
            if not line.strip(): continue
            parts=[x.strip() for x in line.split('|')]
            if len(parts)!=2 or not all(parts): raise forms.ValidationError('每行需要英文与中文两部分，用 | 分开。')
            rows.append(dict(zip(['en','zh'], parts)))
        return rows
    def clean_activity_lines(self):
        rows=[]
        for line in self.cleaned_data['activity_lines'].splitlines():
            if not line.strip(): continue
            parts=[x.strip() for x in line.split('|')]
            if len(parts)<3 or len(parts)>5 or not parts[1].isdigit(): raise forms.ValidationError('每行至少填写步骤、分钟和说明，用 | 分开。分钟请填整数。')
            parts += [''] * (5-len(parts))
            rows.append(dict(zip(['title','minutes','instruction','prompt','task'], parts)))
        return rows
    def clean(self):
        data=super().clean()
        student=data.get('student')
        lessons=data.get('lessons')
        if student and lessons is not None:
            allowed=set(student.courses.values_list('pk',flat=True))
            if any(l.course_id not in allowed for l in lessons):self.add_error('lessons','请先在学生档案中分配所选小课对应的课程。')
        return data
    def save(self, commit=True):
        self.instance.expressions=self.cleaned_data['expression_lines']
        self.instance.activities=self.cleaned_data['activity_lines']
        return super().save(commit)

import json
import subprocess
import tempfile
from pathlib import Path
from .models import Recording

class RecordingAdminForm(forms.ModelForm):
    class Meta:
        model=Recording
        fields='__all__'
    def clean_file(self):
        upload=self.cleaned_data.get('file')
        if not upload or not hasattr(upload,'content_type'): return upload
        if Path(upload.name).suffix.lower()!='.mp4': raise forms.ValidationError('只接受 MP4（H.264/AAC）文件。')
        if upload.size>2*1024**3: raise forms.ValidationError('单个录像最多 2GB，请先压缩或分段。')
        header=upload.read(12);upload.seek(0)
        if header[4:8]!=b'ftyp': raise forms.ValidationError('文件内容不是有效的 MP4 容器。')
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4') as temporary:
                for chunk in upload.chunks(): temporary.write(chunk)
                temporary.flush()
                result=subprocess.run(['ffprobe','-protocol_whitelist','file,pipe','-v','error','-show_streams','-show_format','-of','json',temporary.name], capture_output=True, timeout=45, check=True)
                metadata=json.loads(result.stdout)
                if result.stderr.strip(): raise forms.ValidationError('视频数据有损坏，请重新导出后上传。')
                subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-protocol_whitelist','file,pipe','-i',temporary.name,'-map','0:v:0','-frames:v','1','-f','null','-'], capture_output=True, timeout=30, check=True)
            videos=[s for s in metadata['streams'] if s['codec_type']=='video']
            audio=[s for s in metadata['streams'] if s['codec_type']=='audio']
            if not videos or any((s.get('codec_name')!='h264' or s.get('pix_fmt') not in ['yuv420p','yuvj420p']) for s in videos) or any(s.get('codec_name')!='aac' for s in audio):
                raise forms.ValidationError('请导出为 H.264 视频 + AAC 音频的 MP4，再上传。')
            self.verified_duration=max(1,round(float(metadata['format']['duration'])))
        except (subprocess.SubprocessError, OSError, ValueError, KeyError):
            raise forms.ValidationError('无法验证这个视频，请确认文件完整且编码正确。')
        finally: upload.seek(0)
        return upload
    def save(self, commit=True):
        if hasattr(self,'verified_duration'): self.instance.duration=self.verified_duration
        return super().save(commit)

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from .models import ContentBlock
class ContentBlockForm(forms.ModelForm):
    option_lines=forms.CharField(label='选择题选项（每行一个）',required=False,widget=forms.Textarea(attrs={'rows':4}),help_text='正确选项填上面列表中的序号，从 1 开始。')
    class Meta:
        model=ContentBlock
        exclude=['options']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['correct_choice'].required=False
        if self.instance.pk:self.fields['option_lines'].initial='\n'.join(self.instance.options)
    def clean(self):
        data=super().clean()
        self.instance.options=[line.strip() for line in data.get('option_lines','').splitlines() if line.strip()]
        if not data.get('correct_choice'):data['correct_choice']=1
        upload=data.get('file');kind=data.get('kind')
        if upload and hasattr(upload,'content_type'):
            try:
                if kind=='video':
                    helper=RecordingAdminForm();helper.cleaned_data={'file':upload};helper.clean_file()
                else:
                    ext=Path(upload.name).suffix.lower()
                    allowed={'image':{'.jpg','.jpeg','.png','.webp'},'audio':{'.mp3','.m4a','.ogg'},'document':{'.pdf'}}
                    if kind not in allowed or ext not in allowed[kind]:raise forms.ValidationError('文件扩展名与内容类型不匹配。')
                    if upload.size>100*1024**2:raise forms.ValidationError('此类型文件最大 100MB。')
                    header=upload.read(12);upload.seek(0)
                    if kind=='document':
                        if not header.startswith(b'%PDF-'):raise forms.ValidationError('文件不是有效 PDF。')
                        try:
                            reader=PdfReader(upload,strict=True)
                            if reader.is_encrypted or not len(reader.pages):raise ValueError('需要未加密且包含页面的 PDF。')
                            for page in reader.pages:
                                if page.mediabox.width<=0 or page.mediabox.height<=0:raise ValueError('页面尺寸无效。')
                        except (PyPdfError,ValueError,TypeError,KeyError,RecursionError) as exc:
                            raise forms.ValidationError('PDF 无法解析，请重新导出完整且未加密的文件。') from exc
                    if kind=='image':
                        matches={'.png':header.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':header.startswith(b'\xff\xd8\xff'),'.jpeg':header.startswith(b'\xff\xd8\xff'),'.webp':header.startswith(b'RIFF') and header[8:12]==b'WEBP'}
                        if not matches.get(ext):raise forms.ValidationError('图片内容与文件格式不匹配。')
                    if kind in ('image','audio'):
                        with tempfile.NamedTemporaryFile(suffix=ext) as temp:
                            for chunk in upload.chunks():temp.write(chunk)
                            temp.flush()
                            r=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_streams','-of','json',temp.name],capture_output=True,text=True,timeout=30,check=True)
                        streams=json.loads(r.stdout).get('streams',[])
                        if kind=='audio' and (not streams or any(s['codec_type']!='audio' for s in streams)):raise forms.ValidationError('音频文件无法识别或含有视频流。')
                        if kind=='image' and (not streams or not any(s.get('width',0)>0 for s in streams)):raise forms.ValidationError('图片无法解码。')
            except forms.ValidationError as exc:self.add_error('file',exc)
            except (subprocess.SubprocessError,OSError,ValueError,KeyError):self.add_error('file','无法验证素材文件，请检查文件完整性。')
            finally:upload.seek(0)
        return data
