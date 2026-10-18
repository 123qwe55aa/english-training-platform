from django.db.models import Prefetch
from django.db.models import Q, F
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe
from .models import Session, Lesson, Badge, Recording, Student
from .student_context import resolve_student, student_courses, reward_config

def progress_context(student=None):
    student=student or Student.objects.get(slug="jason")
    courses=student_courses(student)
    total_lessons=student.planned_lessons or max(1,Lesson.objects.filter(course__in=courses,published=True).count())
    total_sessions=student.planned_sessions
    sessions = Session.objects.filter(student=student,published=True).prefetch_related(Prefetch('lessons',queryset=Lesson.objects.filter(published=True,course__in=courses)))
    completed = sessions.filter(status='completed').count()
    lessons = Lesson.objects.filter(published=True, course__in=courses, session__in=sessions.filter(status='completed')).distinct().count()
    return {'library_courses':courses.prefetch_related(Prefetch('lessons',queryset=Lesson.objects.filter(published=True))), 'sessions': sessions, 'next_session': sessions.exclude(status='completed').first(), 'completed_sessions': completed, 'completed_lessons': lessons, 'session_pct': min(100, round(completed / total_sessions * 100, 1)), 'lesson_pct': min(100, round(lessons / total_lessons * 100, 1)), 'badges': Badge.objects.filter(student=student,visible=True, awarded_date__isnull=False), 'planned_sessions':total_sessions, 'planned_lessons':total_lessons}

@require_safe
def home(request, student_slug=None):
    student=resolve_student(request,student_slug)
    return render(request, 'courses/home.html', {**progress_context(student), 'nav':'home'})

@require_safe
def lessons(request, student_slug=None):
    student=resolve_student(request,student_slug)
    return render(request, 'courses/lessons.html', {**progress_context(student), 'nav':'lessons'})

@require_safe
def progress(request, student_slug=None):
    student=resolve_student(request,student_slug)
    return render(request, 'courses/progress.html', {**progress_context(student), 'nav':'progress'})

@require_safe
def session_detail(request, pk, student_slug=None):
    student=resolve_student(request,student_slug)
    session = get_object_or_404(Session.objects.filter(student=student,published=True).prefetch_related(Prefetch('lessons',queryset=Lesson.objects.filter(published=True,course__in=student_courses(student)))), pk=pk)
    from urllib.parse import urlsplit
    has_voa=any(urlsplit(lesson.source_url).hostname=='learningenglish.voanews.com' for lesson in session.lessons.all())
    return render(request, 'courses/session_detail.html', {'has_voa':has_voa,'session': session, 'review': session.review_sentences.splitlines(), 'nav':'lessons', 'recordings': session.recordings.filter(student=student,published=True, consent_confirmed=True)})

@require_safe
def recordings(request, student_slug=None):
    student=resolve_student(request,student_slug)
    return render(request, 'courses/recording_list.html', {'recordings':Recording.objects.filter(Q(session__isnull=True)|Q(session__student_id=F('student_id')),student=student,published=True, consent_confirmed=True), 'nav':'recordings'})

@require_safe
def recording_detail(request, pk, student_slug=None):
    student=resolve_student(request,student_slug)
    recording=get_object_or_404(Recording.objects.filter(Q(session__isnull=True)|Q(session__student_id=F('student_id'))), student=student, pk=pk, published=True, consent_confirmed=True)
    return render(request,'courses/recording_detail.html',{'recording':recording,'chapters':recording.chapters.filter(published=True),'nav':'recordings'})

@require_safe
def recording_stream(request, pk, student_slug=None):
    student=resolve_student(request,student_slug)
    from django.http import HttpResponse, Http404
    from pathlib import PurePosixPath
    record=get_object_or_404(Recording.objects.filter(Q(session__isnull=True)|Q(session__student_id=F('student_id'))), student=student, pk=pk, published=True, consent_confirmed=True)
    name=PurePosixPath(record.file.name)
    if name.is_absolute() or '..' in name.parts or not str(name).startswith('recordings/') or not record.file.storage.exists(record.file.name): raise Http404
    response=HttpResponse(content_type='video/mp4')
    response['X-Accel-Redirect']='/_protected_media/'+str(name)
    response['Cache-Control']='private, no-store'
    return response


def public_material(pk,student=None):
    from .models import LessonMaterial
    query=LessonMaterial.objects.select_related('lesson').filter(lesson_id=pk,published=True,lesson__published=True,lesson__course__published=True)
    if student:query=query.filter(lesson__course__in=student_courses(student))
    return get_object_or_404(query)

@require_safe
def material_detail(request, pk, student_slug=None):
    student=resolve_student(request,student_slug)
    from .models import LessonMaterial
    lesson=get_object_or_404(Lesson,pk=pk,published=True,course__in=student_courses(student))
    material=LessonMaterial.objects.filter(lesson=lesson,published=True).first()
    blocks=lesson.blocks.filter(published=True)
    if not material and not blocks.exists() and LessonMaterial.objects.filter(lesson=lesson).exists():
        from django.http import Http404
        raise Http404
    data=material.data if material else {}
    videos=[dict(data['assets'][key],key=key) for key in data.get('videos',[])]
    questions=[{**q,'clips':[dict(data['assets'][key],key=key) for key in q.get('media',[])]} for q in data.get('quiz',[])]
    return render(request,'courses/material_detail.html',{'material':material,'lesson':lesson,'videos':videos,'questions':questions,'blocks':blocks,'nav':'lessons'})

@require_safe
def material_stream(request, pk, key, student_slug=None):
    student=resolve_student(request,student_slug)
    from django.http import HttpResponse,Http404
    from django.core.files.storage import default_storage
    from pathlib import PurePosixPath
    material=public_material(pk,student)
    asset=material.data.get('assets',{}).get(key)
    if not asset:raise Http404
    name=PurePosixPath(asset.get('file',''))
    if name.is_absolute() or '..' in name.parts or not str(name).startswith(f'voa/lesson-{material.lesson.number:02d}/') or not default_storage.exists(str(name)):raise Http404
    response=HttpResponse(content_type='image/jpeg' if asset.get('kind')=='image' else 'video/mp4')
    response['X-Accel-Redirect']='/_protected_media/'+str(name)
    response['Cache-Control']='private, no-store'
    return response


@require_safe
def reward_summary(request,student_slug=None):
    from django.http import JsonResponse
    student=resolve_student(request,student_slug)
    response=JsonResponse(reward_config(student,request.student_prefix))
    response['Cache-Control']='no-store'
    return response

@require_safe
def resource_stream(request,pk,student_slug=None):
    from .models import ContentBlock
    from pathlib import PurePosixPath
    from django.http import HttpResponse,Http404
    student=resolve_student(request,student_slug)
    block=get_object_or_404(ContentBlock,pk=pk,published=True,lesson__published=True,lesson__course__in=student_courses(student))
    name=PurePosixPath(block.file.name)
    if block.kind not in ('video','audio','image','document') or name.is_absolute() or '..' in name.parts or not str(name).startswith('resources/') or not block.file.storage.exists(str(name)):raise Http404
    mime={'.mp4':'video/mp4','.mp3':'audio/mpeg','.m4a':'audio/mp4','.ogg':'audio/ogg','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.pdf':'application/pdf'}.get(name.suffix)
    if not mime:raise Http404
    response=HttpResponse(content_type=mime)
    response['X-Accel-Redirect']='/_protected_media/'+str(name)
    response['Cache-Control']='private, no-store'
    response['Content-Disposition']='inline; filename="'+name.name+'"'
    return response
