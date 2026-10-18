import json
import shutil
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from courses.models import Lesson, LessonMaterial
from courses.voa import archive_lesson, write_document

class Command(BaseCommand):
    help='Archive official VOA source video, script and quiz; import selected lessons without changing course progress.'
    def add_arguments(self,parser):
        parser.add_argument('--start',type=int,default=1)
        parser.add_argument('--end',type=int,default=12)
        parser.add_argument('--archive',default='storage/voa')
        parser.add_argument('--offline',action='store_true',help='Import existing verified archive without network')
        parser.add_argument('--publish',action='store_true',help='Publish imported materials')
        parser.add_argument('--document',default='storage/voa/VOA-Lesson-1-12.md')
    def handle(self,*args,**o):
        if not 1<=o['start']<=o['end']<=52:raise CommandError('Lesson range must be within 1–52')
        root=Path(o['archive']);records=[];errors=[]
        for n in range(o['start'],o['end']+1):
            try:
                candidates=Lesson.objects.filter(number=n,source_url__startswith='https://learningenglish.voanews.com/')
                if candidates.count()!=1:raise ValueError('Expected exactly one configured VOA lesson')
                lesson=candidates.get()
                if o['offline']:data=json.loads((root/f'lesson-{n:02d}.json').read_text())
                else:data=archive_lesson(n,lesson.source_url,root)
                if data['number']!=n or data['source_url']!=lesson.source_url:raise ValueError('Archive source does not match configured lesson')
                import hashlib
                verified=[]
                for asset in data['assets'].values():
                    rel=Path(asset['file'])
                    if rel.is_absolute() or '..' in rel.parts or not str(rel).startswith(f'voa/lesson-{n:02d}/'):raise ValueError('Invalid archived media path')
                    source=root/'media'/f'lesson-{n:02d}'/rel.name
                    with source.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
                    if digest!=asset['sha256'] or source.stat().st_size!=asset['bytes']:raise ValueError('Media checksum mismatch')
                    verified.append((asset,source,digest,rel.suffix))
                # Content-addressed destinations keep the previous published version intact.
                # Validate the entire lesson before creating any public media.
                for asset,source,digest,suffix in verified:
                    rel=Path(f'voa/lesson-{n:02d}')/(digest+suffix)
                    target=Path(settings.MEDIA_ROOT)/rel;target.parent.mkdir(parents=True,exist_ok=True)
                    if not target.exists():
                        import uuid
                        staged=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
                        try:
                            shutil.copy2(source,staged)
                            staged.replace(target)
                        finally:staged.unlink(missing_ok=True)
                    else:
                        with target.open('rb') as f:existing=hashlib.file_digest(f,'sha256').hexdigest()
                        if existing!=digest:raise ValueError('Existing published media is corrupt; restore backup before importing')
                    asset['file']=rel.as_posix()
                data['lesson_pk']=lesson.pk
                defaults={'data':data}
                if o['publish']:defaults['published']=True
                LessonMaterial.objects.update_or_create(lesson=lesson,defaults=defaults)
                records.append(data)
                self.stdout.write(f'Lesson {n}: {len(data["videos"])} videos, {len(data["transcript"])} script lines, {len(data["quiz"])} quiz questions')
            except Exception as exc:
                errors.append(f'Lesson {n}: {exc}')
                self.stderr.write(errors[-1])
        if records:
            doc=Path(o['document']);doc.parent.mkdir(parents=True,exist_ok=True);write_document(records,doc)
        if errors:raise CommandError('Some lessons failed; existing material for those lessons was retained.\n'+'\n'.join(errors))
        self.stdout.write(self.style.SUCCESS(f'Imported {len(records)} lessons. Document: {o["document"]}'))
