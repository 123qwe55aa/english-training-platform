import uuid
from pathlib import Path
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

def recording_path(instance, filename):
    return f'recordings/{uuid.uuid4().hex}.mp4'

def student_slug(): return 'student-'+uuid.uuid4().hex[:10]

def default_student_id():
    return Student.objects.get_or_create(slug='learner',defaults={'name':'Learner','published':True,'planned_sessions':24,'planned_lessons':12,'schedule':''})[0].pk

class Student(models.Model):
    name = models.CharField('学生姓名',max_length=80)
    slug = models.SlugField('专属页面标识',unique=True,default=student_slug,help_text='自动生成，保存后固定；学生无需登录。')
    published = models.BooleanField('公开学生页面',default=False)
    goal = models.TextField('学习目标',blank=True)
    schedule = models.CharField('上课时间说明',max_length=100,blank=True)
    courses = models.ManyToManyField('Course',blank=True,verbose_name='使用的课程')
    planned_sessions = models.PositiveIntegerField('计划课堂次数',default=168,validators=[MinValueValidator(1)])
    planned_lessons = models.PositiveIntegerField('计划小课数量',default=0,help_text='填 0 时按已分配课程的小课数量计算。')
    reward_label = models.CharField('奖励名称',max_length=80,blank=True,help_text='留空时显示“学生姓名 值”。')
    daily_goal = models.PositiveIntegerField('每日奖励目标',default=100,validators=[MinValueValidator(1),MaxValueValidator(100000)])
    low_threshold = models.PositiveIntegerField('低能量阈值',default=20)
    video_points = models.PositiveIntegerField('看完视频奖励',default=10,validators=[MinValueValidator(1),MaxValueValidator(1000)])
    dialogue_points = models.PositiveIntegerField('完成对话奖励',default=10,validators=[MinValueValidator(1),MaxValueValidator(1000)])
    class Meta:
        ordering=['id']
        verbose_name='学生档案'
        verbose_name_plural='学生档案'
    @property
    def reward_name(self): return self.reward_label or f'{self.name} 值'
    def clean(self):
        if self.low_threshold>self.daily_goal/2:raise ValidationError({'low_threshold':'低能量阈值不能超过每日目标的一半。'})
    def __str__(self):return self.name

class Course(models.Model):
    title = models.CharField('课程名称', max_length=200)
    order = models.PositiveIntegerField('顺序', default=1)
    published = models.BooleanField('公开', default=False)
    class Meta:
        ordering = ['order']
        verbose_name = '课程'
        verbose_name_plural = '课程'
    def __str__(self): return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='课程')
    number = models.PositiveIntegerField('小课编号', validators=[MinValueValidator(1)])
    title = models.CharField('标题', max_length=200)
    source_url = models.URLField('官方教材链接', blank=True)
    learning_target = models.TextField('学习目标', blank=True)
    published = models.BooleanField('公开', default=False)
    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['course', 'number'], name='unique_course_lesson')]
        verbose_name = '课程小课'
        verbose_name_plural = '课程小课'
    def __str__(self): return f'Lesson {self.number} · {self.title}'

class Session(models.Model):
    STATUS = [('planned', '待安排'), ('prepared', '已备课'), ('completed', '已授课')]
    student = models.ForeignKey(Student,on_delete=models.PROTECT,default=default_student_id,related_name='sessions',verbose_name='学生')
    number = models.PositiveIntegerField('第几天')
    date = models.DateField('授课日期', null=True, blank=True)
    title = models.CharField('主题', max_length=200)
    subtitle = models.CharField('英文主题', max_length=200, blank=True)
    lessons = models.ManyToManyField(Lesson, blank=True, verbose_name='关联小课')
    status = models.CharField('授课状态', max_length=20, choices=STATUS, default='planned')
    published = models.BooleanField('公开', default=False)
    goal = models.TextField('今天的小目标', blank=True)
    review_sentences = models.TextField('前一天回顾句（每行一句）', blank=True)
    expressions = models.JSONField('表达卡 [{en,zh}]', default=list, blank=True)
    activities = models.JSONField('练习步骤 [{title,minutes,instruction,prompt,task}]', default=list, blank=True)
    b_plan = models.TextField('B 方案', blank=True)
    exit_check = models.TextField('出口检查', blank=True)
    teacher_reflection = models.TextField('教师复盘（仅教师可见）', blank=True)
    class Meta:
        ordering = ['number']
        constraints=[models.UniqueConstraint(fields=['student','number'],name='unique_student_session')]
        verbose_name = '每日课堂'
        verbose_name_plural = '每日课堂'
    def clean(self):
        if self.pk and Session.objects.filter(pk=self.pk).exclude(student_id=self.student_id).exists():
            raise ValidationError({'student':'已有课堂不能更换学生，请为新学生复制或新建课堂。'})
        for field, keys in [('expressions', ('en', 'zh')), ('activities', ('title', 'instruction'))]:
            data = getattr(self, field)
            if not isinstance(data, list) or any(not isinstance(x, dict) or any(not isinstance(x.get(k), str) for k in keys) for x in data):
                raise ValidationError({field: '请填写由指定键组成的对象列表。'})
    def __str__(self): return f'Day {self.number:02d} · {self.title}'

class MasteryRecord(models.Model):
    STATES = [('independent', '独立完成'), ('prompted', '提示后完成'), ('practice', '下次再练')]
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='mastery', verbose_name='课堂')
    task = models.CharField('可观察任务', max_length=200)
    state = models.CharField('掌握记录', max_length=20, choices=STATES)
    evidence = models.TextField('课堂证据（仅教师可见）', blank=True)
    class Meta:
        verbose_name = '课堂证据'
        verbose_name_plural = '课堂证据'
    def __str__(self): return f'{self.session} / {self.task}'

class Badge(models.Model):
    student = models.ForeignKey(Student,on_delete=models.PROTECT,default=default_student_id,related_name='badges',verbose_name='学生')
    name = models.CharField('徽章', max_length=100)
    description = models.TextField('说明')
    awarded_date = models.DateField('获得日期', null=True, blank=True)
    evidence = models.TextField('授予依据（仅教师可见）', blank=True)
    visible = models.BooleanField('公开显示', default=False)
    class Meta:
        verbose_name = '学习徽章'
        verbose_name_plural = '学习徽章'
    def __str__(self): return self.name

class Recording(models.Model):
    student = models.ForeignKey(Student,on_delete=models.PROTECT,default=default_student_id,related_name='recordings',verbose_name='学生')
    session = models.ForeignKey(Session, on_delete=models.PROTECT, null=True, blank=True, related_name='recordings', verbose_name='课堂')
    title = models.CharField('标题', max_length=200)
    date = models.DateField('日期', null=True, blank=True)
    file = models.FileField('MP4 录像', upload_to=recording_path)
    duration = models.PositiveIntegerField('时长（秒）', default=0)
    published = models.BooleanField('公开发布', default=False)
    consent_confirmed = models.BooleanField('已取得录像公开同意', default=False)
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = '课堂录像'
        verbose_name_plural = '课堂录像'
    def clean(self):
        if self.session_id and self.student_id and self.session.student_id!=self.student_id:
            raise ValidationError({'session':'录像与课堂必须属于同一学生。'})
        if self.published and not self.consent_confirmed:
            raise ValidationError({'consent_confirmed': '公开视频需要先确认学习者同意。'})
        if self.file and Path(self.file.name).suffix.lower() != '.mp4':
            raise ValidationError({'file': '请先导出为 MP4（H.264/AAC）再上传。'})
    def __str__(self): return self.title

class ChapterNote(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE, related_name='chapters', verbose_name='录像')
    timestamp = models.PositiveIntegerField('时间戳（秒）')
    note = models.CharField('复盘提示', max_length=300)
    published = models.BooleanField('公开', default=False)
    class Meta:
        ordering = ['timestamp']
        verbose_name = '录像章节'
        verbose_name_plural = '录像章节'
    @property
    def time_label(self): return f'{self.timestamp // 60:02d}:{self.timestamp % 60:02d}'
    def __str__(self): return f'{self.time_label} {self.note}'

class LessonMaterial(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='material', verbose_name='VOA 小课')
    data = models.JSONField('抓取素材及来源', default=dict)
    published = models.BooleanField('公开素材', default=False)
    imported_at = models.DateTimeField('导入时间', auto_now=True)
    class Meta:
        ordering = ['lesson__number']
        verbose_name = 'VOA 原版素材'
        verbose_name_plural = 'VOA 原版素材'
    def __str__(self): return str(self.lesson)


class RewardEntry(models.Model):
    student = models.ForeignKey(Student,on_delete=models.PROTECT,related_name='teacher_rewards',verbose_name='学生')
    date = models.DateField('奖励日期',default=timezone.localdate)
    title = models.CharField('奖励原因（学生可见）',max_length=200)
    amount = models.IntegerField('奖励点数（负数为调整扣回）',validators=[MinValueValidator(-100000),MaxValueValidator(100000)])
    class Meta:
        ordering=['-date','-id']
        verbose_name='教师奖励记录'
        verbose_name_plural='教师奖励记录'
    def __str__(self):return f'{self.student} · {self.title} · {self.amount:+d}'

def resource_path(instance,filename):
    return f'resources/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'

class ContentBlock(models.Model):
    KINDS=[('text','文字／Script'),('video','视频 MP4'),('audio','音频'),('image','图片／绘本页'),('document','PDF 文档'),('dialogue','对话练习'),('quiz','选择题')]
    lesson=models.ForeignKey(Lesson,on_delete=models.CASCADE,related_name='blocks',verbose_name='所属小课')
    title=models.CharField('标题',max_length=200)
    order=models.PositiveIntegerField('显示顺序',default=1)
    kind=models.CharField('内容类型',max_length=20,choices=KINDS,default='text')
    published=models.BooleanField('公开此内容',default=False)
    file=models.FileField('素材文件',upload_to=resource_path,blank=True)
    text=models.TextField('文字／台词／图片说明',blank=True)
    question=models.TextField('题干',blank=True)
    options=models.JSONField('选项',default=list,blank=True)
    correct_choice=models.PositiveIntegerField('正确选项序号（从 1 开始）',default=1)
    explanation=models.TextField('答案解释',blank=True)
    class Meta:
        ordering=['order','id']
        verbose_name='教材内容块'
        verbose_name_plural='教材内容块'
    @property
    def answer_index(self):return self.correct_choice-1
    def clean(self):
        if self.kind in ('video','audio','image','document') and not self.file:raise ValidationError({'file':'此类型需要上传素材文件。'})
        if self.file and self.kind in ('video','audio','image','document'):
            allowed={'video':{'.mp4'},'audio':{'.mp3','.m4a','.ogg'},'image':{'.jpg','.jpeg','.png','.webp'},'document':{'.pdf'}}
            if Path(self.file.name).suffix.lower() not in allowed[self.kind]:raise ValidationError({'file':'文件扩展名与内容类型不匹配。'})
        if self.kind in ('text','dialogue') and not self.text.strip():raise ValidationError({'text':'请填写文字或对话台词。'})
        if self.kind=='quiz':
            if not self.question.strip() or not isinstance(self.options,list) or len(self.options)<2 or any(not isinstance(x,str) or not x.strip() for x in self.options):raise ValidationError({'question':'选择题需要题干和至少两个非空选项。'})
            if not 1<=self.correct_choice<=len(self.options):raise ValidationError({'correct_choice':'正确选项序号超出范围。'})
    def __str__(self):return f'{self.lesson} / {self.title}'

class AgentOperation(models.Model):
    request_id=models.CharField('请求编号',max_length=100,unique=True)
    tool=models.CharField('工具',max_length=80)
    fingerprint=models.CharField(max_length=64)
    actor=models.CharField('操作者',max_length=80,default='codex-ssh')
    arguments=models.JSONField('请求内容',default=dict)
    before=models.JSONField('修改前',default=dict)
    after=models.JSONField('修改后',default=dict)
    result=models.JSONField('执行结果',default=dict)
    created_at=models.DateTimeField('执行时间',auto_now_add=True)
    class Meta:
        ordering=['-id']
        verbose_name='Agent 操作记录'
        verbose_name_plural='Agent 操作记录'
    def __str__(self):return f'{self.tool} / {self.request_id}'
