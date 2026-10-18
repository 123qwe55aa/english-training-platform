"""Private staging, opaque handles only; staging is never a public media path."""
import hashlib,os,re,uuid
from pathlib import Path
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from .schema import ToolError
HANDLE=re.compile(r'[0-9a-f]{32}\.(mp4|mp3|m4a|ogg|png|jpg|jpeg|webp|pdf)\Z')
MAX_SIZE=2*1024**3

def root():return Path(getattr(settings,'AGENT_UPLOAD_ROOT',Path(settings.MEDIA_ROOT).parent/'agent_uploads'))
def stage(stream,name,size):
    suffix=Path(name).suffix.lower()
    handle=uuid.uuid4().hex+suffix
    if not HANDLE.fullmatch(handle) or type(size)is not int or not 0<size<=MAX_SIZE:raise ToolError('invalid_upload','Unsupported file type or size (maximum 2 GB).')
    folder=root();folder.mkdir(parents=True,exist_ok=True);os.chmod(folder,0o700)
    path=folder/handle;digest=hashlib.sha256();remaining=size
    try:
        with path.open('xb') as output:
            os.chmod(path,0o600)
            while remaining:
                chunk=stream.read(min(1024*1024,remaining))
                if not chunk:raise ToolError('invalid_upload','Upload ended before declared size.')
                output.write(chunk);digest.update(chunk);remaining-=len(chunk)
            if stream.read(1):raise ToolError('invalid_upload','Upload exceeds declared size.')
    except BaseException:
        path.unlink(missing_ok=True);raise
    return {'upload_handle':handle,'size':size,'sha256':digest.hexdigest()}

def open_upload(handle):
    if not HANDLE.fullmatch(handle):raise ToolError('invalid_upload','Invalid upload handle; paths are not accepted.')
    path=root()/handle
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root().resolve()):raise ToolError('invalid_upload','Upload handle is missing or unavailable. Upload the local file first.')
    if path.stat().st_size>MAX_SIZE:raise ToolError('invalid_upload','File too large.')
    return path,UploadedFile(path.open('rb'),name=handle,content_type='application/octet-stream',size=path.stat().st_size)
