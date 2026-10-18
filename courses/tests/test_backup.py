import sqlite3
import tempfile
from pathlib import Path
from unittest import TestCase
from courses.backup import create_backup, verify_backup
class BackupTest(TestCase):
    def test_database_and_media_can_be_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);db=root/'live.sqlite3';media=root/'media';media.mkdir()
            con=sqlite3.connect(db);con.execute('CREATE TABLE courses_session (title TEXT)');con.execute("INSERT INTO courses_session VALUES ('Hello')");con.commit();con.close()
            (media/'clip.mp4').write_bytes(b'test-video-payload')
            archive=create_backup(db,media,root/'backups')
            result=verify_backup(archive)
            self.assertEqual(result['media_files'],1)
            self.assertEqual(result['sessions'],1)
            self.assertEqual(archive.stat().st_mode & 0o777,0o600)
    def test_missing_media_directory_rejects_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);db=root/'live.sqlite3'
            with sqlite3.connect(db) as con: con.execute('CREATE TABLE courses_session (title TEXT)')
            with self.assertRaises(ValueError): create_backup(db,root/'missing',root/'backups')
    def test_missing_referenced_recording_rejects_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);db=root/'live.sqlite3';media=root/'media';media.mkdir()
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE courses_session (title TEXT)')
                con.execute('CREATE TABLE courses_recording (file TEXT)')
                con.execute("INSERT INTO courses_recording VALUES ('recordings/missing.mp4')")
            with self.assertRaises(ValueError): create_backup(db,media,root/'backups')
    def test_missing_voa_asset_rejects_backup(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);db=root/'live.sqlite3';media=root/'media';media.mkdir()
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE courses_session (title TEXT)')
                con.execute('CREATE TABLE courses_lessonmaterial (data TEXT)')
                con.execute('INSERT INTO courses_lessonmaterial VALUES (?)',(json.dumps({'assets':{'main':{'file':'voa/lesson-01/missing.mp4'}}}),))
            with self.assertRaises(ValueError):create_backup(db,media,root/'backups')
    def test_missing_uploaded_content_is_not_a_successful_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);db=root/'live.sqlite3';media=root/'media';media.mkdir()
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE courses_session (title TEXT)')
                con.execute('CREATE TABLE courses_contentblock (file TEXT)')
                con.execute("INSERT INTO courses_contentblock VALUES ('resources/missing.pdf')")
            with self.assertRaises(ValueError):create_backup(db,media,root/'backups')
