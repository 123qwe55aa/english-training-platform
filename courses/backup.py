import hashlib
import json
import os
import sqlite3
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

def digest_file(path: Path) -> str:
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def referenced_media(database: Path) -> list[str]:
    with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as db:
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        paths=[]
        if 'courses_recording' in tables:
            paths.extend(row[0] for row in db.execute("SELECT file FROM courses_recording WHERE file != ''"))
        if 'courses_contentblock' in tables:
            paths.extend(row[0] for row in db.execute("SELECT file FROM courses_contentblock WHERE file != ''"))
        if 'courses_lessonmaterial' in tables:
            for (raw,) in db.execute('SELECT data FROM courses_lessonmaterial'):
                paths.extend(asset['file'] for asset in json.loads(raw).get('assets',{}).values())
        return paths

def require_media(database: Path, media: Path) -> None:
    if not database.is_file() or not media.is_dir(): raise ValueError('Database or media directory missing; backup aborted')
    for rel in referenced_media(database):
        file=media/rel
        if not file.resolve().is_relative_to(media.resolve()) or file.is_symlink() or not file.is_file(): raise ValueError('Referenced recording missing: '+rel)

def create_backup(database: Path, media: Path, destination: Path) -> Path:
    require_media(database,media)
    destination.mkdir(parents=True,exist_ok=True)
    os.chmod(destination,0o700)
    name='english-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.tar.gz'
    archive=destination/name
    with tempfile.TemporaryDirectory() as work:
        root=Path(work);db=root/'db.sqlite3'
        with sqlite3.connect(database) as source, sqlite3.connect(db) as target: source.backup(target)
        require_media(db,media)
        manifest={'media':{}}
        for file in media.rglob('*'):
            if file.is_file() and not file.is_symlink(): manifest['media'][file.relative_to(media).as_posix()]=digest_file(file)
        manifest['database']=digest_file(db)
        (root/'manifest.json').write_text(json.dumps(manifest))
        fd=os.open(archive,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as output, tarfile.open(fileobj=output,mode='w:gz') as tar:
            tar.add(db,arcname='db.sqlite3');tar.add(root/'manifest.json',arcname='manifest.json')
            for rel in manifest['media']:tar.add(media/rel,arcname='media/'+rel)
    return archive

def verify_backup(archive: Path) -> dict:
    with tempfile.TemporaryDirectory() as work:
        root=Path(work)
        with tarfile.open(archive,'r:gz') as tar:tar.extractall(root,filter='data')
        manifest=json.loads((root/'manifest.json').read_text())
        require_media(root/'db.sqlite3', root/'media') if referenced_media(root/'db.sqlite3') else None
        if digest_file(root/'db.sqlite3')!=manifest['database']:raise ValueError('Database checksum mismatch')
        for rel,digest in manifest['media'].items():
            file=root/'media'/rel
            if not file.resolve().is_relative_to(root.resolve()) or digest_file(file)!=digest:raise ValueError('Media checksum mismatch')
        with sqlite3.connect(f'file:{root}/db.sqlite3?mode=ro',uri=True) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed')
            sessions=db.execute('SELECT COUNT(*) FROM courses_session').fetchone()[0]
        return {'media_files':len(manifest['media']),'sessions':sessions,'integrity':'ok'}
