"""VOA Level 1 importer. Keeps plain text, original quiz answers and source provenance."""
import hashlib
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

ORIGIN='https://learningenglish.voanews.com'
ALLOWED={'learningenglish.voanews.com','voa-video-ns.akamaized.net','voa-video-ns.akamaized.net.cn','voa-audio.voanews.eu','voa-video.voanews.eu','gdb.voanews.com'}
CREDIT='Source: VOA Learning English — learningenglish.voanews.com. VOA-produced educational content; public-domain reuse with credit: https://learningenglish.voanews.com/p/6861.html'

def validate_url(url):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in ALLOWED or p.username or p.password or p.port not in (None,443):
        raise ValueError('Only approved HTTPS VOA sources are supported')
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

OPENER=urllib.request.build_opener(SafeRedirect)

def fetch(url, target, binary=False):
    validate_url(url)
    target=Path(target)
    if target.exists():return target
    target.parent.mkdir(parents=True,exist_ok=True)
    part=target.with_suffix(target.suffix+'.part')
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'EnglishTeachingArchive/1.0 (educational personal archive)'})
            with OPENER.open(req,timeout=90) as r, part.open('wb') as f:
                validate_url(r.url)
                total=0
                while chunk:=r.read(1024*1024):
                    total+=len(chunk)
                    if total>(512*1024*1024 if binary else 8*1024*1024):raise ValueError('Source exceeds size limit')
                    f.write(chunk)
                expected=r.headers.get('Content-Length')
                if expected and total!=int(expected):raise ValueError('Incomplete source download')
                if not total:raise ValueError('Empty source download')
            part.replace(target)
            time.sleep(.2)
            return target
        except Exception:
            part.unlink(missing_ok=True)
            if attempt==2:raise
            time.sleep(2**attempt)

def text(tag):return tag.get_text(' ',strip=True).replace('\u200b','').strip() if tag else ''

def media(soup):
    result=[]
    for v in soup.select('video'):
        sources=json.loads(v.get('data-sources','[]'))
        # 360p keeps the original source and is practical for home-server streaming.
        chosen=next((s.get('Src') for s in sources if s.get('DataInfo')=='360p'),None) or v.get('src')
        if chosen and chosen not in [m['url'] for m in result]:result.append({'title':v.get('title','Video'),'url':validate_url(chosen),'quality':'360p' if sources else 'source'})
    return result

def parse_lesson(html):
    soup=BeautifulSoup(html,'html.parser')
    transcript=[]
    heading=next((h for h in soup.select('.wsw h2,.wsw h3') if text(h).lower() in ('conversation','conversation script','script')),None)
    if heading:
        for el in heading.next_siblings:
            if getattr(el,'name',None) in ('h2','h3'):break
            if not getattr(el,'name',None):continue
            if el.select('video,audio') or 'wsw__embed' in el.get('class',[]):continue
            for junk in el.select('script,style'):junk.decompose()
            blocks=[node for node in el.select('p,div') if not node.select('p,div')]
            for block in blocks or [el]:
                for br in block.select('br'):br.replace_with('|||VOA-LINE|||')
                for line in block.get_text(' ',strip=True).split('|||VOA-LINE|||'):
                    line=re.sub(r'\s+([.,!?;:])',r'\1',line).strip()
                    if line:transcript.append(line)
    quiz=soup.select_one('[data-ajax-url*="/Quiz/Start"]')
    match=re.search(r'[?&]id=(\d+)',quiz.get('data-ajax-url','')) if quiz else None
    return {'title':text(soup.h1),'transcript':transcript,'videos':media(soup),'quiz_id':match.group(1) if match else None}

def parse_quiz(html):
    soup=BeautifulSoup(html,'html.parser')
    caption=text(soup.select_one('.caption'))
    match=re.search(r'Question\s+(\d+)\s*/\s*(\d+)',caption)
    if not match:raise ValueError('Quiz question/count not found')
    answers=soup.select('.quiz__answers-item')
    correct=[i for i,a in enumerate(answers) if 'quiz__answers-item--correct' in a.get('class',[])]
    if len(correct)!=1:raise ValueError('Official answer is absent or ambiguous')
    images=[]
    for img in soup.select('.quiz__answers-img img'):
        # Video posters are not question images; video itself is archived instead.
        if not img.find_parent(class_='media-pholder') and img.get('src'):
            images.append({'title':img.get('alt','Quiz image'),'url':validate_url(urljoin(ORIGIN,img['src'])),'kind':'image'})
    q={'number':int(match.group(1)),'question':text(soup.select_one('.quiz__question-title')),'options':[text(a.select_one('.quiz__answers-item-text')) for a in answers],'answer':correct[0],'explanation':text(soup.select_one('form p.clear')),'media':media(soup)+images}
    return q,int(match.group(2))

def validate_video(path):
    import subprocess
    result=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries','stream=codec_name,codec_type,pix_fmt','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError('Downloaded video is invalid: '+Path(path).name)
    info=json.loads(result.stdout)
    streams=info.get('streams',[])
    video=[s for s in streams if s.get('codec_type')=='video']
    if not video or any(s.get('codec_name')!='h264' or s.get('pix_fmt') not in ('yuv420p','yuvj420p') for s in video):raise ValueError('Video must be browser-playable H.264')
    if any(s.get('codec_name')!='aac' for s in streams if s.get('codec_type')=='audio'):raise ValueError('Audio must be browser-playable AAC')
    duration=float(info.get('format',{}).get('duration',0))
    if not duration>0:raise ValueError('Video has no duration')
    return {'duration':round(duration,2)}

def archive_lesson(number,url,root):
    root=Path(root);raw=root/'raw';destination=root/'media'/f'lesson-{number:02d}'
    manifest=root/f'lesson-{number:02d}.json'
    baseline=json.loads(manifest.read_text()).get('assets',{}) if manifest.exists() else {}
    page=fetch(url,raw/f'lesson-{number:02d}.html').read_text()
    data=parse_lesson(page)
    if not data['transcript'] or not data['videos']:raise ValueError('Missing transcript or lesson video; refusing incomplete lesson')
    data.update(number=number,source_url=url,fetched_at=datetime.now(timezone.utc).isoformat(),credit=CREDIT,quiz=[],assets={})
    def asset(item):
        key=hashlib.sha256(item['url'].encode()).hexdigest()[:20]
        extension='.jpg' if item.get('kind')=='image' else '.mp4'
        cached=(destination/(key+extension)).exists()
        file=fetch(item['url'],destination/(key+extension),binary=True)
        if extension=='.mp4':item.update(validate_video(file))
        with file.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        previous=baseline.get(key)
        if cached and previous and previous['sha256']!=digest:raise ValueError('Cached media checksum changed; remove the corrupt cached file and retry: '+str(file))
        data['assets'][key]={**item,'file':f'voa/lesson-{number:02d}/{file.name}','bytes':file.stat().st_size,'sha256':digest}
        return key
    data['videos']=[asset(v) for v in data['videos']]
    if data['quiz_id']:
        # VOA's public read-only Start endpoint exposes question/result pairs.
        pageindex=2
        while True:
            qu=ORIGIN+f'/Quiz/Start?id={data["quiz_id"]}&page={pageindex}&isEmbedded=True'
            question,total=parse_quiz(fetch(qu,raw/f'lesson-{number:02d}-quiz-{pageindex}.html').read_text())
            if question['number']!=pageindex//2:raise ValueError('Unexpected quiz pagination')
            question['source_url']=qu
            question['media']=[asset(v) for v in question['media']]
            data['quiz'].append(question)
            if len(data['quiz'])==total:break
            if pageindex>100:raise ValueError('Quiz exceeds safe page limit')
            pageindex+=2
    data['quiz_status']='complete' if data['quiz'] else 'not_present_on_source'
    output=root/f'lesson-{number:02d}.json';tmp=output.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(output)
    return data

def write_document(records,destination,base_url='https://example.com'):
    numbers=[d['number'] for d in records]
    lines=[f'# VOA Level 1 · Lesson {min(numbers)}–{max(numbers)} 课程素材汇编','',CREDIT,'','此文档收录原版英文对话、视频入口和听力测验（含官方答案）。网站可直接播放已保存的视频；答题不会自动改变学习进度。','']
    for d in records:
        lines += [f'## Lesson {d["number"]} · {d["title"]}','',f'来源：{d["source_url"]}',f'抓取时间（UTC）：{d["fetched_at"]}',f'站内学习页：{base_url}/materials/{d["lesson_pk"]}/','', '### 视频','']
        for key in d['videos']:
            a=d['assets'][key];lines.append(f'- [{a["title"]}]({base_url}/materials/{d["lesson_pk"]}/media/{key}/) · {a["quality"]} · {a["bytes"]/1048576:.1f} MB')
        lines+=['','### Script · 原版对话','']+['\n\n'.join(d['transcript']),'','### Quiz · 原版听力测验','']
        if not d['quiz']:lines+=['原课程页未提供可提取测验。','']
        for q in d['quiz']:
            lines += [f'#### {q["number"]}. {q["question"]}','']
            for key in q['media']:lines.append(f'- [题目素材]({base_url}/materials/{d["lesson_pk"]}/media/{key}/)')
            lines += [f'- **{chr(65+i)}.** {option}' for i,option in enumerate(q['options'])]
            lines += ['',f'官方答案：{chr(65+q["answer"])}. {q["options"][q["answer"]]}',q['explanation'],f'答案来源：{q["source_url"]}','']
    Path(destination).write_text('\n'.join(lines))
