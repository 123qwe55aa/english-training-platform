from django.contrib import admin
from .models import Course, Lesson, Session, MasteryRecord, Badge, Recording, ChapterNote, LessonMaterial, Student, RewardEntry, ContentBlock
from .forms import SessionAdminForm, RecordingAdminForm, ContentBlockForm

admin.site.site_header = '英语小院 · 教师工作台'
admin.site.site_title = '英语小院管理'
admin.site.index_title = '今天，带朋友向前一小步'

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title','order','published']
    search_fields=['title']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['number','title','course','published']
    list_filter = ['course','published']
    search_fields = ['title']

class MasteryInline(admin.TabularInline):
    model = MasteryRecord
    extra = 0

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    form = SessionAdminForm
    list_display = ['student','number','title','date','status','published']
    list_filter = ['student','status','published']
    search_fields = ['title']
    filter_horizontal = ['lessons']
    inlines = [MasteryInline]
    fieldsets = [('课堂信息', {'fields':['student','number','title','subtitle','date','status','published','lessons']}), ('学生可见的学习流程', {'fields':['goal','review_sentences','expression_lines','activity_lines','b_plan','exit_check']}), ('教师复盘 · 仅你可见', {'fields':['teacher_reflection'], 'description':'目标说清 → 先尝试 → 等待 → 判断卡点 → 最小提示 → 再试 → 撤提示 → 记录证据。下次只调整一项教学行为。'})]

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display=['student','name','awarded_date','visible']
    list_filter=['visible']

class ChapterInline(admin.TabularInline):
    model=ChapterNote
    extra=0

@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    form=RecordingAdminForm
    list_display=['student','title','session','date','duration','published','consent_confirmed']
    list_filter=['published','consent_confirmed']
    inlines=[ChapterInline]

@admin.register(LessonMaterial)
class LessonMaterialAdmin(admin.ModelAdmin):
    list_display=['lesson','imported_at','published']
    list_filter=['published']
    readonly_fields=['lesson','data','imported_at']
    def has_add_permission(self,request): return False


class StudentSessionInline(admin.TabularInline):
    model=Session
    fields=['number','title','date','status','published']
    extra=0
    show_change_link=True

class RewardInline(admin.TabularInline):
    model=RewardEntry
    extra=0

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display=['name','published','daily_goal','video_points','dialogue_points','student_page']
    search_fields=['name','slug']
    filter_horizontal=['courses']
    inlines=[StudentSessionInline,RewardInline]
    actions=['copy_learner_plan']
    @admin.action(description='复制 Learner 的课堂安排（不复制已完成状态）')
    def copy_learner_plan(self,request,queryset):
        from .student_services import copy_plan
        source=Student.objects.get(slug='learner')
        total=sum(copy_plan(source,target) for target in queryset)
        self.message_user(request,f'已新建 {total} 次课堂；已有记录保持原状。请先为学生选择使用的课程。')
    fieldsets=[('学生资料',{'fields':['name','slug','published','goal','schedule','courses']}),('学习计划',{'fields':['planned_sessions','planned_lessons']}),('奖励规则',{'fields':['reward_label','daily_goal','low_threshold','video_points','dialogue_points']})]
    def get_readonly_fields(self,request,obj=None):return ['slug'] if obj else []
    @admin.display(description='学生页面')
    def student_page(self,obj):
        from django.utils.html import format_html
        return format_html('<a href="/s/{}/" target="_blank">打开页面 ↗</a>',obj.slug)
    def has_delete_permission(self,request,obj=None):
        return False if obj and obj.slug=='learner' else super().has_delete_permission(request,obj)

@admin.register(RewardEntry)
class RewardAdmin(admin.ModelAdmin):
    list_display=['student','date','title','amount']
    list_filter=['student','date']
    search_fields=['title','student__name']

class ContentInline(admin.StackedInline):
    model=ContentBlock
    form=ContentBlockForm
    extra=0
    show_change_link=True
    fields=['title','kind','order','published','file','text','question','option_lines','correct_choice','explanation']

@admin.register(ContentBlock)
class ContentAdmin(admin.ModelAdmin):
    form=ContentBlockForm
    fields=['lesson','title','kind','order','published','file','text','question','option_lines','correct_choice','explanation']
    list_display=['title','lesson','kind','order','published']
    list_filter=['kind','published','lesson__course']
    search_fields=['title','text','lesson__title']
    autocomplete_fields=['lesson']

LessonAdmin.inlines=[ContentInline]
admin.site.index_title='管理学生、课程素材与学习记录'

from .models import AgentOperation
@admin.register(AgentOperation)
class AgentOperationAdmin(admin.ModelAdmin):
    list_display=['created_at','tool','request_id','actor']
    list_filter=['tool']
    search_fields=['request_id','tool']
    readonly_fields=[field.name for field in AgentOperation._meta.fields]
    actions=None
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False
