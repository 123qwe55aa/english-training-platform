# VOA course archive and website integration

This extension imports the existing configured VOA Level 1 lesson URLs. It adds original source materials to the existing teacher-led sessions; it does not create mastery records, award badges, or change taught-session status.

## Run

Install `requirements.txt`, migrate, and initialize the existing lesson list if this is a new installation. Then:

```sh
python scripts/scrape_voa.py --start 1 --end 12 --publish
```

Equivalent: `python manage.py import_voa --start 1 --end 12 --publish`.

- Defaults: archive in `storage/voa`, consolidated Markdown in `storage/voa/VOA-Lesson-1-12.md`.
- `--document PATH` selects the Markdown destination.
- Without `--publish`, existing visibility is preserved and newly imported material remains unpublished.
- `--offline` imports the existing archive, verifies every media SHA-256 and size, and does not contact VOA.
- Cached raw HTML and complete media are reused. Incomplete `.part` downloads are replaced on retry. Remove a cached lesson HTML/quiz page to refresh the corresponding source. Completed files are not downloaded again.
- Supports configured lessons 1–52; this delivery imports only 1–12. Set up later lesson URLs before extending the range.
- Failed lessons are reported with nonzero exit status; their previous DB material is retained. Successful lessons are imported individually and included in the document.

## Archive format

`storage/voa/lesson-NN.json` holds source URL, UTC fetch time, credit, dialogue lines, video IDs, original quiz questions/options/answers/explanations, source result-page URLs, and asset checksums. `storage/voa/media/lesson-NN/` holds media. Cache HTML stays in `storage/voa/raw/`.

The source main video, speaking practice and pronunciation video are all retained at original 360p to limit home-server bandwidth. Quiz clips are separate original videos. Public read-only `/Quiz/Start` result pages expose official correct-answer markers; the scraper does not submit quiz answers or guess an answer from the dialogue. Missing source quizzes are labelled absent. An absent/ambiguous official answer is an error, not a generated replacement.

Imported media is copied into Django's `MEDIA_ROOT/voa/`. The archive/cache is excluded from Git and Docker images. Do not put video binaries in the Obsidian Git vault; the consolidated document links to site playback endpoints.

## Publication and playback

Each session links to its two materials pages under `/materials/<lesson-pk>/`. Each page contains HTML5 video players, plain escaped dialogue, and local interactive original quizzes. Questions provide immediate feedback without changing learner progress. Users can retry or consult the source.

Every media request goes through a Django gate requiring a published material, lesson and course, then uses the existing Nginx internal media location. Direct `/media/` remains blocked. Unpublishing any parent revokes both the page and playback. Materials are managed in the teacher admin as `VOA 原版素材`. Classroom recordings and their learner-consent workflow are separate.

## Sources and scope

VOA permits reuse of its own Learning English material with attribution: https://learningenglish.voanews.com/p/6861.html . The archive targets the VOA-created Let's Learn English teaching series. Third-party news-agency content is outside this importer’s scope. External HTML/JS is never embedded in the local site.

Only allowlisted HTTPS source/media hosts are fetched, including redirect targets. Downloads have timeouts, three attempts, size limits and atomic final writes. Per-file checksums are verified on import. Backups include all imported media and detect missing DB-referenced VOA assets.

## Live import into Coolify

The public site runs in the Coolify app container on `fedora@10.144.144.5`, identified by application UUID `hy8qh7tcaxb6lqtofb7jn7vc`. Do not import through the legacy Compose checkout; it has a separate database. The live container mounts `/data` persistently and uses `/data/media` for protected course assets.

Archive the exact configured lesson URLs returned by `materials.get` or `courses.list` without importing into a local database:

```sh
.venv/bin/python - <<'PY'
from courses.voa import archive_lesson
archive_lesson(13, 'https://learningenglish.voanews.com/a/lets-learn-english-lesson-13-happy-birthday-william-shakespeare/3312239.html', '/tmp/voa-live-archive')
archive_lesson(14, 'https://learningenglish.voanews.com/a/lets-learn-english-lesson-14-how-about-this/3323771.html', '/tmp/voa-live-archive')
PY
tar -czf /tmp/voa-live-archive.tar.gz -C /tmp/voa-live-archive .
scp /tmp/voa-live-archive.tar.gz fedora@10.144.144.5:/tmp/voa-live-archive.tar.gz
```

On the home host, extract the archive, copy it into the unique live app container, and run the checksum-verifying importer:

```sh
ssh fedora@10.144.144.5
container=$(docker ps --filter label=coolify.applicationUuid=hy8qh7tcaxb6lqtofb7jn7vc --filter label=com.docker.compose.service=app --format '{{.Names}}')
mkdir -p /tmp/voa-live-archive && tar -xzf /tmp/voa-live-archive.tar.gz -C /tmp/voa-live-archive
docker cp /tmp/voa-live-archive "$container":/tmp/voa-live-archive
docker exec --user 0:0 "$container" chown -R 10001:10001 /tmp/voa-live-archive
docker exec "$container" python manage.py import_voa --start 13 --end 14 --archive /tmp/voa-live-archive --offline --publish --document /data/VOA-Lesson-13-14.md
```

Use the actual lesson range and source URLs for each import. The command verifies that each archive matches the configured source URL and checks every media checksum and type. It updates lesson materials only, not session completion, mastery, rewards, or teacher reflection. Read the resulting `materials.get` record and verify the student page and protected media streams. Remove the temporary archive from the host and app container after verification; retain `/data/VOA-Lesson-*.md` when a consolidated text document is useful.
