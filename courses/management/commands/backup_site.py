from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from courses.backup import create_backup, verify_backup
class Command(BaseCommand):
    help='Back up SQLite and media, then verify recovery in a temporary directory.'
    def handle(self,*args,**options):
        archive=create_backup(Path(settings.DATABASES['default']['NAME']),Path(settings.MEDIA_ROOT),Path(settings.DATABASES['default']['NAME']).parent/'backups')
        self.stdout.write(f'{archive.name}: {verify_backup(archive)}')
        for old in sorted(archive.parent.glob('english-*.tar.gz'), reverse=True)[7:]: old.unlink()
