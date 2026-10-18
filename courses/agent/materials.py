import hashlib
from courses.models import Lesson,ContentBlock,LessonMaterial,Course
from courses.forms import ContentBlockForm
from .schema import ToolError
from .snapshots import snapshot,get,canonical
from .uploads import open_upload

def material_snapshot(lesson):
    data=snapshot(lesson);data.pop('revision')
    data['blocks']=[snapshot(b) for b in lesson.blocks.all()]
    legacy=LessonMaterial.objects.filter(lesson=lesson).first()
    data['voa_material']=snapshot(legacy) if legacy else None
    data['revision']=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def material_get(args,ctx):return {'material':material_snapshot(get(Lesson,args['lesson_id']))},{}

def material_import(args,ctx):
    if args.get('lesson_id'):
        lesson=get(Lesson,args['lesson_id']);before=material_snapshot(lesson)
        if args.get('expected_revision')!=before['revision']:raise ToolError('stale_revision','Read materials.get and use material.revision.')
        if args.get('course_id') and args['course_id']!=lesson.course_id:raise ToolError('invalid_arguments','An existing lesson cannot move to another course.')
    else:
        if not args.get('course_id'):raise ToolError('invalid_arguments','New material requires course_id.')
        lesson=Lesson(course=get(Course,args['course_id']));before={}
    for key,value in args['fields'].items():setattr(lesson,key,value)
    lesson.full_clean();lesson.save()
    from django.db.models import Max
    start=(lesson.blocks.aggregate(value=Max('order'))['value'] or 0)+1
    created=[]
    for index,raw in enumerate(args['blocks']):
        data=dict(raw);handle=data.pop('upload_handle',None);options=data.pop('options',[])
        if any(not option.strip() or option.splitlines()!=[option] for option in options):raise ToolError('invalid_arguments','Each quiz option must be a nonempty single line; blank options or line separators would change the answer mapping.')
        data.setdefault('order',start+index);data['lesson']=lesson.pk;data['option_lines']='\n'.join(options)
        opened=None
        try:
            files={}
            if handle:
                path,opened=open_upload(handle);files['file']=opened
            form=ContentBlockForm(data=data,files=files)
            if not form.is_valid():raise ToolError('validation_error',f'Material block {index+1} failed validation.',form.errors.get_json_data())
            block=form.save(commit=False)
            # Register the file before the database save so rollback can remove it.
            if block.file:
                block.file.save(block.file.name,block.file.file,save=False);ctx['files'].append(block.file)
            block.save();created.append(block.pk)
            if handle:ctx['consume'].append(path)
        finally:
            if opened:opened.close()
    return {'material':material_snapshot(lesson),'created_block_ids':created,'admin':f'/admin/courses/lesson/{lesson.pk}/change/','public':f'/materials/{lesson.pk}/','publication_note':'Student must be assigned the course; student, course, lesson and blocks must be published.'},before
