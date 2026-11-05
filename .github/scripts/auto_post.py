#!/usr/bin/env python3
"""Post a Central PA Report markdown package to social platforms.

Credentials come only from the environment (GitHub Actions secrets).
This file never contains tokens.

Caption text is taken from the package's public story sections
(visual hook, Instagram caption, Facebook post, live URL). Ops notes,
pitches, and draft banners are not posted.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

GRAPH_VERSION = "v25.0"  # supported through 2028-07-29
LINKEDIN_VERSION = "202610"  # October 2026; supported through 2027-10-15
DEFAULT_CONTENT_FILE = "social-media-package-2026-11-04.md"
MEDIA_DIR_ENV = "MEDIA_DIR"
TRUNCATION_NOTE = "\n\n[truncated]"

# Hard platform caps. Facebook's API allows far more; 5,000 keeps a post readable.
LIMIT_INSTAGRAM = 2200
LIMIT_FACEBOOK = 5000
LIMIT_LINKEDIN = 3000
LIMIT_X = 280
LIMIT_TIKTOK = 2200
LIMIT_YOUTUBE_TITLE = 100
LIMIT_YOUTUBE_DESCRIPTION = 5000
LIMIT_PINTEREST_TITLE = 100
LIMIT_PINTEREST_DESCRIPTION = 800
LIMIT_PINTEREST_ALT = 500

SECRET_NAMES = (
    "INSTAGRAM_ACCESS_TOKEN",
    "INSTAGRAM_ACCOUNT_ID",
    "FACEBOOK_ACCESS_TOKEN",
    "FACEBOOK_PAGE_ID",
    "LINKEDIN_ACCESS_TOKEN",
    "LINKEDIN_AUTHOR_URN",
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
    "TIKTOK_ACCESS_TOKEN",
    "TIKTOK_OPEN_ID",
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
    "PINTEREST_ACCESS_TOKEN",
    "PINTEREST_BOARD_ID",
    "MEDIA_IMAGE_URL",
    "CONTENT_FILE",
)

PLATFORMS = ("instagram", "facebook", "linkedin", "youtube", "tiktok", "x", "pinterest")
VIDEO_PLATFORMS = {"youtube", "tiktok"}
PLATFORM_LABELS = {
    "instagram": "Instagram",
    "facebook": "Facebook",
    "linkedin": "LinkedIn",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "x": "X",
    "pinterest": "Pinterest",
}

BG_COLOR = "0x0A2540"
GOLD = "0xD4A017"
BODY_COLOR = "0xE6EDF5"
INTRO_SECONDS = 4.0
OUTRO_SECONDS = 4.0
MAX_SHORT_SECONDS = 60.0


class ApiError(Exception):
    """A platform call failed. The message must not include credentials."""


@dataclass
class Outcome:
    status: str  # ok, skipped, failed
    detail: str


@dataclass
class Story:
    title: str
    hook: str
    url: str
    instagram: str
    facebook: str
    hashtags: str


@dataclass
class Package:
    date_line: str
    stories: list[Story] = field(default_factory=list)
    fallback_body: str = ""


@dataclass
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def redact(text: str) -> str:
    """Remove credential-shaped substrings before anything is logged."""
    values = [os.environ.get(name, "") for name in SECRET_NAMES]
    for value in values:
        if len(value) >= 6:
            text = text.replace(value, "[redacted]")
    text = re.sub(
        r"(?i)(access_token|refresh_token|client_secret|oauth_token_secret|oauth_token)=([^&\s]+)",
        r"\1=[redacted]",
        text,
    )
    text = re.sub(r"(?i)authorization:\s*\S+", "authorization: [redacted]", text)
    text = re.sub(r"(?i)\bbearer\s+\S+", "Bearer [redacted]", text)
    text = re.sub(r"(?i)\boauth\s+\S+", "OAuth [redacted]", text)
    return text[:1500]


def scrub(text: str) -> str:
    return redact(text)


def write_outputs(status: str, detail: str) -> None:
    detail = detail.replace("\r", " ").replace("\n", " ").replace("%", "")
    detail = re.sub(r"\s+", " ", detail).strip()
    if len(detail) > 400:
        detail = detail[:397] + "..."
    print(f"[{status}] {detail}")
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"status={status}\n")
            handle.write(f"detail={detail}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"**{status}.** {detail}\n\n")


def content_file() -> pathlib.Path:
    raw = os.environ.get("CONTENT_FILE", "").strip() or DEFAULT_CONTENT_FILE
    path = pathlib.Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(
            "CONTENT_FILE must be a repo-relative path such as "
            f"{DEFAULT_CONTENT_FILE}"
        )
    return path


def media_dir() -> pathlib.Path:
    raw = os.environ.get(MEDIA_DIR_ENV, "build/social").strip() or "build/social"
    return pathlib.Path(raw)


def find_media(name: str) -> pathlib.Path | None:
    root = media_dir()
    direct = root / name
    if direct.is_file():
        return direct
    if root.is_dir():
        matches = sorted(root.rglob(name))
        if matches:
            return matches[0]
    return None


def missing_secrets(names: list[str]) -> list[str]:
    return [name for name in names if not os.environ.get(name, "").strip()]


def missing_message(names: list[str]) -> str:
    joined = ", ".join(names)
    return (
        f"Missing GitHub Actions secrets: {joined}. "
        "Add them under Settings > Secrets and variables > Actions."
    )


def md_to_text(value: str) -> str:
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r"\1 \2", value)
    return value.strip()


def extract_subsection(block: str, heading_prefix: str) -> str:
    lines = block.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("### "):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def parse_story(chunk: str) -> Story:
    title_match = re.match(r"^# STORY \d+\s+[—–-]\s+(.+)", chunk)
    title = title_match.group(1).strip() if title_match else "Central PA Report"
    hook_match = re.search(
        r"\*\*Visual hook(?: \([^)]*\))?:\*\*\s+\*\*(.+?)\*\*",
        chunk,
    )
    hook = hook_match.group(1).strip() if hook_match else title
    url_match = re.search(r"\*\*Live URL:\*\*\s+(https?://\S+)", chunk)
    url = url_match.group(1).rstrip(").,") if url_match else ""
    hashtags = " ".join(
        re.findall(
            r"#[A-Za-z0-9_]+",
            extract_subsection(chunk, "### (4) Hashtags"),
        )
    )
    return Story(
        title=title,
        hook=hook,
        url=url,
        instagram=md_to_text(extract_subsection(chunk, "### (2) Instagram micro-blog caption")),
        facebook=md_to_text(extract_subsection(chunk, "### (3) Facebook post")),
        hashtags=hashtags,
    )


def fallback_body(text: str) -> str:
    cut = re.split(r"^# \(8\)|^## Ops checklist", text, maxsplit=1, flags=re.M)[0]
    kept = []
    for line in cut.splitlines():
        lowered = line.lower()
        if "draft only" in lowered:
            continue
        if "do not post" in lowered:
            continue
        kept.append(line)
    return md_to_text("\n".join(kept)).strip()


def parse_package(text: str) -> Package:
    date_match = re.search(r"\*\*Date:\*\*\s*(.+)", text)
    date_line = md_to_text(date_match.group(1)).strip() if date_match else ""
    stories: list[Story] = []
    for chunk in re.split(r"(?=^# STORY \d+\b)", text, flags=re.M):
        if re.match(r"^# STORY \d+\b", chunk):
            stories.append(parse_story(chunk))
    return Package(date_line=date_line, stories=stories, fallback_body=fallback_body(text))


def load_package(path: pathlib.Path | None = None) -> tuple[Package, pathlib.Path]:
    path = path or content_file()
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"Content file is empty: {path}")
    return parse_package(text), path


def truncate(text: str, limit: int) -> tuple[str, bool]:
    text = text.strip()
    if len(text) <= limit:
        return text, False
    if limit <= len(TRUNCATION_NOTE):
        return text[:limit], True
    budget = limit - len(TRUNCATION_NOTE)
    cut = text[:budget]
    for separator in ("\n", " "):
        index = cut.rfind(separator)
        if index >= int(budget * 0.6):
            cut = cut[:index]
            break
    cut = cut.rstrip()
    result = cut + TRUNCATION_NOTE
    if len(result) > limit:
        result = cut[: limit - len(TRUNCATION_NOTE)].rstrip() + TRUNCATION_NOTE
    return result, True


def clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    if limit < 2:
        return text[:limit]
    cut = text[: limit - 1].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    result = cut + "…"
    if len(result) > limit:
        result = text[:limit]
    return result


def join_parts(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def facebook_caption(package: Package) -> str:
    if not package.stories:
        text, _ = truncate(package.fallback_body, LIMIT_FACEBOOK)
        return text
    blocks = []
    for story in package.stories:
        block = story.facebook or story.instagram or story.hook
        if story.url and story.url not in block:
            block = f"{block}\n\n{story.url}"
        blocks.append(block)
    text, _ = truncate(join_parts(blocks), LIMIT_FACEBOOK)
    return text


def instagram_caption(package: Package) -> str:
    if not package.stories:
        text, _ = truncate(package.fallback_body, LIMIT_INSTAGRAM)
        return text
    blocks = []
    tags: list[str] = []
    for story in package.stories:
        block = story.instagram or story.facebook or story.hook
        if story.url and story.url not in block:
            block = f"{block}\n{story.url}"
        blocks.append(block)
        for tag in story.hashtags.split():
            if tag not in tags:
                tags.append(tag)
    body = join_parts(blocks)
    footer = " ".join(tags)
    if footer and len(body) + 2 + len(footer) <= LIMIT_INSTAGRAM:
        return f"{body}\n\n{footer}"
    text, _ = truncate(body, LIMIT_INSTAGRAM)
    return text


def escape_little(text: str) -> str:
    """Escape LinkedIn little-text reserved characters so they post as plain text."""
    return re.sub(r"([\\|{}\[\]()<>#*_~@])", r"\\\1", text)


def _snap_boundary(chunk: str, floor: int) -> str:
    for separator in ("\n\n", "\n", ". "):
        index = chunk.rfind(separator)
        if index >= floor:
            end = index + (1 if separator == ". " else 0)
            return chunk[:end].rstrip()
    index = chunk.rfind(" ")
    if index >= floor:
        return chunk[:index].rstrip()
    return chunk.rstrip()


def linkedin_text(package: Package) -> str:
    urls = [story.url for story in package.stories if story.url]
    source = facebook_caption(package).strip()
    for url in urls:
        source = source.replace(url, "")
    source = re.sub(r"(?i)\bFull story:\s*", "", source)
    source = re.sub(r"[ \t]+\n", "\n", source)
    source = re.sub(r"\n{3,}", "\n\n", source).strip()
    url_block = "\n".join(urls)

    def render(body: str, truncated: bool) -> str:
        pieces = [body.strip()]
        if truncated:
            pieces.append(TRUNCATION_NOTE.strip())
        if url_block:
            pieces.append(url_block)
        raw = "\n\n".join(piece for piece in pieces if piece)
        return escape_little(raw)

    if len(render(source, False)) <= LIMIT_LINKEDIN:
        return render(source, False)
    best = ""
    low = 0
    high = len(source)
    while low <= high:
        mid = (low + high) // 2
        chunk = _snap_boundary(source[:mid].rstrip(), int(mid * 0.6))
        candidate = render(chunk, True)
        if chunk.strip() and len(candidate) <= LIMIT_LINKEDIN:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best or render(clip(source, 500), True)


def x_text(package: Package) -> str:
    if not package.stories:
        text, _ = truncate(" ".join(package.fallback_body.split()), LIMIT_X)
        return text
    story = package.stories[0]
    hook = " ".join((story.hook or story.title).split())
    url = story.url or "https://www.centralpareport.com"
    extra = f" +{len(package.stories) - 1} more" if len(package.stories) > 1 else ""
    suffix = f"{extra} {url}" if extra else f" {url}"
    room = LIMIT_X - len(suffix)
    if room < 24:
        suffix = f" {url}"
        room = LIMIT_X - len(suffix)
    if len(hook) > room:
        hook = clip(hook, room)
    text = f"{hook}{suffix}".strip()
    if len(text) > LIMIT_X:
        text = text[:LIMIT_X]
    return text


def youtube_title(package: Package) -> str:
    hook = package.stories[0].hook if package.stories else "Central PA Report"
    suffix = " #Shorts"
    return clip(hook, LIMIT_YOUTUBE_TITLE - len(suffix)) + suffix


def youtube_description(package: Package) -> str:
    urls = [story.url for story in package.stories if story.url]
    footer_lines = ["#Shorts", *urls]
    footer = "\n".join(footer_lines)
    room = LIMIT_YOUTUBE_DESCRIPTION - len(footer) - 2
    body, _ = truncate(facebook_caption(package), max(room, 0))
    description = f"{body}\n\n{footer}".strip()
    if len(description) > LIMIT_YOUTUBE_DESCRIPTION:
        description = description[:LIMIT_YOUTUBE_DESCRIPTION]
    return description


def youtube_tags(package: Package) -> list[str]:
    tags = ["Shorts", "Central PA Report", "Pennsylvania"]
    for story in package.stories:
        for tag in re.findall(r"#([A-Za-z0-9_]+)", story.hashtags):
            if tag not in tags:
                tags.append(tag[:30])
    kept: list[str] = []
    total = 0
    for tag in tags:
        if len(kept) >= 12 or total + len(tag) + 1 > 450:
            break
        kept.append(tag)
        total += len(tag) + 1
    return kept


def tiktok_caption(package: Package) -> str:
    text, _ = truncate(instagram_caption(package), LIMIT_TIKTOK)
    return text


def pinterest_title(package: Package) -> str:
    hook = package.stories[0].hook if package.stories else "Central PA Report"
    return clip(hook, LIMIT_PINTEREST_TITLE)


def pinterest_description(package: Package) -> str:
    if not package.stories:
        text, _ = truncate(package.fallback_body, LIMIT_PINTEREST_DESCRIPTION)
        return text
    first = package.stories[0]
    body = first.facebook or first.instagram or first.hook
    others = [story.hook for story in package.stories[1:] if story.hook]
    footer = ("Also: " + "; ".join(others)) if others else ""
    if footer and len(body) + 2 + len(footer) <= LIMIT_PINTEREST_DESCRIPTION:
        return f"{body.strip()}\n\n{footer}"
    text, _ = truncate(body, LIMIT_PINTEREST_DESCRIPTION)
    return text


def pinterest_alt(package: Package) -> str:
    hook = package.stories[0].hook if package.stories else "Central PA Report daily briefing"
    return clip(hook, LIMIT_PINTEREST_ALT)


def first_link(package: Package) -> str:
    for story in package.stories:
        if story.url:
            return story.url
    return ""


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 120,
    follow_redirects: bool = True,
) -> HttpResult:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    handlers = [] if follow_redirects else [_NoRedirect()]
    opener = urllib.request.build_opener(*handlers)
    host = urllib.parse.urlsplit(url).netloc
    try:
        with opener.open(request, timeout=timeout) as response:
            return HttpResult(response.status, dict(response.headers.items()), response.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, dict(exc.headers.items()), exc.read())
    except urllib.error.URLError as exc:
        raise ApiError(f"Network error calling {host}: {exc.reason}") from None


def header_value(result: HttpResult, name: str) -> str:
    for key, value in result.headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def parse_json(result: HttpResult) -> object:
    raw = result.body.decode("utf-8", errors="replace").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def error_summary(result: HttpResult) -> str:
    raw = result.body.decode("utf-8", errors="replace").strip()
    try:
        data = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return redact(raw or f"HTTP {result.status}")
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            parts = [
                str(error.get("code") or ""),
                str(error.get("message") or error.get("error_user_msg") or error.get("type") or ""),
            ]
            summary = " ".join(part for part in parts if part).strip()
            return redact(summary or raw)
        if isinstance(error, str):
            return redact(str(data.get("error_description") or error))
        errors = data.get("errors")
        if isinstance(errors, list):
            messages = []
            for item in errors:
                if isinstance(item, dict):
                    messages.append(str(item.get("message") or item.get("detail") or item))
                else:
                    messages.append(str(item))
            return redact("; ".join(messages))
        if data.get("message"):
            return redact(str(data["message"]))
        if data.get("detail"):
            return redact(str(data["detail"]))
    return redact(raw or f"HTTP {result.status}")


def form_body(fields: dict[str, str]) -> bytes:
    return urllib.parse.urlencode({key: value for key, value in fields.items() if value is not None}).encode()


def require_ok(result: HttpResult, label: str, ok: tuple[int, ...] = (200, 201)) -> dict:
    if result.status not in ok:
        raise ApiError(f"{label} HTTP {result.status}: {error_summary(result)}")
    data = parse_json(result)
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        code = str(data["error"].get("code") or "")
        if code and code.lower() not in {"ok", "0"}:
            raise ApiError(f"{label}: {error_summary(result)}")
    if isinstance(data, dict) and data.get("error") and not isinstance(data.get("error"), dict):
        raise ApiError(f"{label}: {error_summary(result)}")
    return data if isinstance(data, dict) else {}


def graph_post(path: str, fields: dict[str, str]) -> dict:
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip('/')}"
    result = http_request(
        "POST",
        url,
        data=form_body(fields),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return require_ok(result, "Meta Graph")


def graph_get(path: str, fields: dict[str, str]) -> dict:
    query = urllib.parse.urlencode(fields)
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip('/')}?{query}"
    result = http_request("GET", url)
    return require_ok(result, "Meta Graph")


def wait_instagram_container(container_id: str, token: str, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    last = "UNKNOWN"
    while True:
        data = graph_get(container_id, {"fields": "status_code,status", "access_token": token})
        last = str(data.get("status_code") or "UNKNOWN")
        if last == "FINISHED":
            return
        if last in {"ERROR", "EXPIRED"}:
            raise ApiError(f"Instagram media container {last}: {data.get('status') or 'no detail'}")
        if time.time() >= deadline:
            raise ApiError(f"Instagram media container still {last} after {timeout}s")
        time.sleep(5)


def publish_instagram_container(ig_id: str, token: str, container_id: str) -> str:
    data = graph_post(
        f"{ig_id}/media_publish",
        {"creation_id": container_id, "access_token": token},
    )
    media_id = str(data.get("id") or "")
    if not media_id:
        raise ApiError("Instagram publish succeeded without a media id")
    return media_id


def post_instagram() -> Outcome:
    missing = missing_secrets(["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"])
    if missing:
        return Outcome("failed", missing_message(missing))
    package, _path = load_package()
    caption = instagram_caption(package)
    if not caption.strip():
        return Outcome("failed", "Instagram caption extracted from the content file is empty")
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"].strip()
    ig_id = urllib.parse.quote(os.environ["INSTAGRAM_ACCOUNT_ID"].strip(), safe="")
    video = find_media("short.mp4")
    image_url = os.environ.get("MEDIA_IMAGE_URL", "").strip()
    print(f"Instagram caption length: {len(caption)}")
    if video is not None:
        print(f"Instagram: uploading reel from {video.name} ({video.stat().st_size} bytes)")
        created = graph_post(
            f"{ig_id}/media",
            {
                "media_type": "REELS",
                "upload_type": "resumable",
                "caption": caption,
                "share_to_feed": "true",
                "access_token": token,
            },
        )
        container_id = str(created.get("id") or "")
        if not container_id:
            raise ApiError("Instagram did not return a media container id")
        uri = str(created.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{container_id}")
        payload = video.read_bytes()
        uploaded = http_request(
            "POST",
            uri,
            data=payload,
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(len(payload)),
                "Content-Type": "application/octet-stream",
            },
            timeout=300,
        )
        if uploaded.status >= 400:
            raise ApiError(f"Instagram video upload HTTP {uploaded.status}: {error_summary(uploaded)}")
        uploaded_body = parse_json(uploaded)
        if isinstance(uploaded_body, dict) and uploaded_body.get("success") is False:
            raise ApiError(f"Instagram video upload rejected: {error_summary(uploaded)}")
        wait_instagram_container(container_id, token)
        media_id = publish_instagram_container(ig_id, token, container_id)
        return Outcome("ok", f"Instagram reel published (media id {media_id})")
    if image_url:
        print("Instagram: publishing photo from MEDIA_IMAGE_URL")
        created = graph_post(
            f"{ig_id}/media",
            {"image_url": image_url, "caption": caption, "access_token": token},
        )
        container_id = str(created.get("id") or "")
        if not container_id:
            raise ApiError("Instagram did not return a photo container id")
        wait_instagram_container(container_id, token, timeout=90)
        media_id = publish_instagram_container(ig_id, token, container_id)
        return Outcome("ok", f"Instagram photo published (media id {media_id})")
    return Outcome(
        "skipped",
        "Instagram needs the generated short (prepare-media) or the MEDIA_IMAGE_URL secret. "
        "Feed photos require a public image URL. Reels use the rendered 1080x1920 video.",
    )


def post_facebook() -> Outcome:
    missing = missing_secrets(["FACEBOOK_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"])
    if missing:
        return Outcome("failed", missing_message(missing))
    package, _path = load_package()
    caption = facebook_caption(package)
    if not caption.strip():
        return Outcome("failed", "Facebook caption extracted from the content file is empty")
    token = os.environ["FACEBOOK_ACCESS_TOKEN"].strip()
    page_id = urllib.parse.quote(os.environ["FACEBOOK_PAGE_ID"].strip(), safe="")
    image_url = os.environ.get("MEDIA_IMAGE_URL", "").strip()
    print(f"Facebook caption length: {len(caption)}")
    if image_url:
        data = graph_post(
            f"{page_id}/photos",
            {"url": image_url, "caption": caption, "access_token": token},
        )
        return Outcome("ok", f"Facebook photo published (id {data.get('id') or 'unknown'})")
    data = graph_post(
        f"{page_id}/feed",
        {"message": caption, "access_token": token},
    )
    return Outcome("ok", f"Facebook text post published (id {data.get('id') or 'unknown'})")


def post_linkedin() -> Outcome:
    missing = missing_secrets(["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN"])
    if missing:
        return Outcome("failed", missing_message(missing))
    author = os.environ["LINKEDIN_AUTHOR_URN"].strip()
    if not re.fullmatch(r"urn:li:(person|organization):[A-Za-z0-9_-]+", author):
        return Outcome(
            "failed",
            "LINKEDIN_AUTHOR_URN must look like urn:li:person:... or urn:li:organization:...",
        )
    package, _path = load_package()
    commentary = linkedin_text(package)
    if not commentary.strip():
        return Outcome("failed", "LinkedIn caption extracted from the content file is empty")
    print(f"LinkedIn commentary length: {len(commentary)} (little-text escaped; image upload is not part of v1)")
    payload = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    result = http_request(
        "POST",
        "https://api.linkedin.com/rest/posts",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN'].strip()}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": LINKEDIN_VERSION,
        },
    )
    require_ok(result, "LinkedIn", ok=(200, 201))
    post_id = header_value(result, "x-restli-id") or "created"
    return Outcome("ok", f"LinkedIn text post published ({post_id})")


def youtube_access_token() -> str:
    result = http_request(
        "POST",
        "https://oauth2.googleapis.com/token",
        data=form_body(
            {
                "client_id": os.environ["YOUTUBE_CLIENT_ID"].strip(),
                "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"].strip(),
                "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
                "grant_type": "refresh_token",
            }
        ),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    data = parse_json(result)
    token = data.get("access_token") if isinstance(data, dict) else None
    if result.status >= 400 or not token:
        message = ""
        if isinstance(data, dict):
            message = str(data.get("error_description") or data.get("error") or "")
        raise ApiError(f"YouTube token refresh failed (HTTP {result.status}). {message}".strip())
    print("YouTube access token refreshed.")
    return str(token)


def post_youtube() -> Outcome:
    missing = missing_secrets(["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"])
    if missing:
        return Outcome("failed", missing_message(missing))
    video = find_media("short.mp4")
    if video is None:
        return Outcome("failed", "short.mp4 is missing. The prepare-media job must render the vertical short first.")
    info = probe_media(video)
    if info["width"] != 1080 or info["height"] != 1920:
        return Outcome("failed", f"YouTube Short must be 1080x1920, got {info['width']}x{info['height']}")
    if not 3 <= info["duration"] <= MAX_SHORT_SECONDS:
        return Outcome("failed", f"YouTube Short duration {info['duration']:.1f}s is outside 3–60s")
    package, _path = load_package()
    title = youtube_title(package)
    description = youtube_description(package)
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": youtube_tags(package),
            "categoryId": "25",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }
    token = youtube_access_token()
    size = video.stat().st_size
    init = http_request(
        "POST",
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(metadata).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": "video/mp4",
        },
        follow_redirects=False,
    )
    if init.status >= 400:
        raise ApiError(f"YouTube upload session HTTP {init.status}: {error_summary(init)}")
    location = header_value(init, "Location")
    if not location:
        raise ApiError("YouTube upload session did not return a Location header")
    payload = video.read_bytes()
    uploaded = http_request(
        "PUT",
        location,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(len(payload)),
            "Content-Range": f"bytes 0-{len(payload) - 1}/{len(payload)}",
        },
        timeout=300,
    )
    data = require_ok(uploaded, "YouTube upload")
    video_id = str(data.get("id") or "")
    if not video_id:
        raise ApiError("YouTube upload finished without a video id")
    return Outcome("ok", f"YouTube Short published https://www.youtube.com/shorts/{video_id} title={title!r}")


def plan_tiktok_chunks(size: int) -> tuple[list[tuple[int, int]], int]:
    if size <= 0:
        raise ApiError("Video file is empty")
    max_single = 64 * 1024 * 1024
    if size <= max_single:
        return [(0, size)], size
    chunk_size = 10 * 1024 * 1024
    count = size // chunk_size
    if count < 1 or count > 1000:
        raise ApiError(f"TikTok chunk plan is invalid for a {size}-byte video")
    ranges = []
    for index in range(count):
        start = index * chunk_size
        end = size if index == count - 1 else start + chunk_size
        ranges.append((start, end))
    return ranges, chunk_size


def tiktok_json(token: str, url: str, payload: dict, label: str) -> dict:
    result = http_request(
        "POST",
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        timeout=120,
    )
    return require_ok(result, label)


def verify_tiktok_open_id(token: str, expected: str) -> str:
    result = http_request(
        "GET",
        "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name",
        headers={"Authorization": f"Bearer {token}"},
    )
    if result.status >= 400:
        return (
            f"Could not verify TIKTOK_OPEN_ID (user info HTTP {result.status}: {error_summary(result)}). "
            "Continuing with the access token."
        )
    data = parse_json(result)
    error = data.get("error") if isinstance(data, dict) else None
    code = str((error or {}).get("code") or "") if isinstance(error, dict) else ""
    if code and code.lower() != "ok":
        return f"Could not verify TIKTOK_OPEN_ID ({code}). Continuing with the access token."
    user = {}
    if isinstance(data, dict):
        body = data.get("data") if isinstance(data.get("data"), dict) else {}
        user = body.get("user") if isinstance(body.get("user"), dict) else body
    actual = str(user.get("open_id") or "")
    if actual and actual != expected:
        raise ApiError("TIKTOK_OPEN_ID does not match the account for TIKTOK_ACCESS_TOKEN.")
    if not actual:
        return "TikTok user info did not include open_id. Continuing with the access token."
    return "TikTok open_id matches the access token."


def post_tiktok() -> Outcome:
    missing = missing_secrets(["TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"])
    if missing:
        return Outcome("failed", missing_message(missing))
    video = find_media("short.mp4")
    if video is None:
        return Outcome("failed", "short.mp4 is missing. The prepare-media job must render the vertical short first.")
    info = probe_media(video)
    if not 3 <= info["duration"] <= MAX_SHORT_SECONDS:
        return Outcome("failed", f"TikTok video duration {info['duration']:.1f}s is outside 3–60s")
    token = os.environ["TIKTOK_ACCESS_TOKEN"].strip()
    print(verify_tiktok_open_id(token, os.environ["TIKTOK_OPEN_ID"].strip()))
    creator = tiktok_json(token, "https://open.tiktokapis.com/v2/post/publish/creator_info/query/", {}, "TikTok creator info")
    creator_data = creator.get("data") if isinstance(creator.get("data"), dict) else {}
    options = [str(item) for item in creator_data.get("privacy_level_options") or []]
    preferred = ["PUBLIC_TO_EVERYONE", "FOLLOWER_OF_CREATOR", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"]
    privacy = next((item for item in preferred if item in options), "")
    if not privacy:
        raise ApiError(
            "TikTok creator_info did not offer a usable privacy_level. "
            f"Options: {', '.join(options) or 'none'}."
        )
    if privacy != "PUBLIC_TO_EVERYONE":
        print(
            f"::warning::TikTok will post as {privacy}. "
            "Unaudited Content Posting apps often only allow SELF_ONLY until TikTok audits the app."
        )
    max_duration = int(creator_data.get("max_video_post_duration_sec") or 0)
    if max_duration and info["duration"] > max_duration:
        raise ApiError(f"Video is {info['duration']:.1f}s and this TikTok account allows {max_duration}s")
    package, _path = load_package()
    caption = tiktok_caption(package)
    payload_bytes = video.read_bytes()
    ranges, chunk_size = plan_tiktok_chunks(len(payload_bytes))
    init = tiktok_json(
        token,
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        {
            "post_info": {
                "title": caption,
                "privacy_level": privacy,
                "disable_duet": bool(creator_data.get("duet_disabled")),
                "disable_comment": bool(creator_data.get("comment_disabled")),
                "disable_stitch": bool(creator_data.get("stitch_disabled")),
                "video_cover_timestamp_ms": 1000,
                "brand_content_toggle": False,
                "brand_organic_toggle": True,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": len(payload_bytes),
                "chunk_size": chunk_size,
                "total_chunk_count": len(ranges),
            },
        },
        "TikTok init",
    )
    init_data = init.get("data") if isinstance(init.get("data"), dict) else {}
    publish_id = str(init_data.get("publish_id") or "")
    upload_url = str(init_data.get("upload_url") or "")
    if not publish_id or not upload_url:
        raise ApiError("TikTok init did not return publish_id and upload_url")
    for start, end in ranges:
        chunk = payload_bytes[start:end]
        uploaded = http_request(
            "PUT",
            upload_url,
            data=chunk,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end - 1}/{len(payload_bytes)}",
            },
            timeout=300,
        )
        if uploaded.status not in {201, 206}:
            raise ApiError(f"TikTok chunk upload HTTP {uploaded.status}: {error_summary(uploaded)}")
    status_name = "PROCESSING_UPLOAD"
    for _ in range(12):
        status_body = tiktok_json(
            token,
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            {"publish_id": publish_id},
            "TikTok status",
        )
        status_data = status_body.get("data") if isinstance(status_body.get("data"), dict) else {}
        status_name = str(status_data.get("status") or "UNKNOWN")
        if status_name == "PUBLISH_COMPLETE":
            break
        if status_name == "FAILED":
            reason = status_data.get("fail_reason") or status_data.get("error") or "no reason"
            raise ApiError(f"TikTok publish failed: {reason}")
        time.sleep(5)
    return Outcome(
        "ok",
        f"TikTok upload accepted (publish_id {publish_id}, privacy {privacy}, status {status_name})",
    )


def oauth_percent(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def oauth1_sign(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str,
    token_secret: str,
    extra_params: dict[str, str] | None = None,
    nonce: str | None = None,
    timestamp: str | None = None,
) -> tuple[str, str]:
    parts = urllib.parse.urlsplit(url)
    base_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    collected = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    if extra_params:
        collected.update(extra_params)
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    collected.update(oauth_params)
    encoded_items = sorted((oauth_percent(key), oauth_percent(value)) for key, value in collected.items())
    parameter_string = "&".join(f"{key}={value}" for key, value in encoded_items)
    base_string = "&".join([method.upper(), oauth_percent(base_url), oauth_percent(parameter_string)])
    signing_key = f"{oauth_percent(consumer_secret)}&{oauth_percent(token_secret)}"
    digest = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode()
    oauth_params["oauth_signature"] = signature
    header = "OAuth " + ", ".join(
        f'{oauth_percent(key)}="{oauth_percent(value)}"' for key, value in sorted(oauth_params.items())
    )
    return header, signature


def multipart_body(field: str, filename: str, content: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = "----CentralPAReport" + secrets.token_hex(12)
    crlf = b"\r\n"
    body = b"".join(
        [
            f"--{boundary}".encode() + crlf,
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"'.encode() + crlf,
            f"Content-Type: {content_type}".encode() + crlf + crlf,
            content + crlf,
            f"--{boundary}--".encode() + crlf,
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def download_bytes(url: str, limit: int = 5_000_000) -> bytes:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise ApiError("MEDIA_IMAGE_URL must be an http(s) URL")
    result = http_request("GET", url, timeout=60)
    if result.status >= 400:
        raise ApiError(f"Could not download MEDIA_IMAGE_URL (HTTP {result.status})")
    if len(result.body) > limit:
        raise ApiError("MEDIA_IMAGE_URL is larger than 5 MB")
    if not result.body:
        raise ApiError("MEDIA_IMAGE_URL downloaded an empty file")
    return result.body


def x_image_bytes() -> tuple[bytes, str] | None:
    pin = find_media("pin.jpg")
    if pin is not None:
        return pin.read_bytes(), "pin.jpg"
    image_url = os.environ.get("MEDIA_IMAGE_URL", "").strip()
    if not image_url:
        return None
    return download_bytes(image_url), "media-image"


def post_x() -> Outcome:
    missing = missing_secrets(["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"])
    if missing:
        return Outcome("failed", missing_message(missing))
    package, _path = load_package()
    text = x_text(package)
    if not text.strip():
        return Outcome("failed", "X caption extracted from the content file is empty")
    print(f"X caption length: {len(text)}")
    consumer_key = os.environ["X_API_KEY"].strip()
    consumer_secret = os.environ["X_API_SECRET"].strip()
    token = os.environ["X_ACCESS_TOKEN"].strip()
    token_secret = os.environ["X_ACCESS_TOKEN_SECRET"].strip()
    media_ids: list[str] = []
    warning = ""
    try:
        image = x_image_bytes()
    except ApiError as exc:
        image = None
        warning = f" Image skipped: {exc}."
        print(f"::warning::{exc}")
    if image is not None:
        content, filename = image
        body, content_type = multipart_body("media", filename, content, "application/octet-stream")
        upload_url = "https://upload.twitter.com/1.1/media/upload.json"
        auth, _signature = oauth1_sign("POST", upload_url, consumer_key, consumer_secret, token, token_secret)
        uploaded = http_request(
            "POST",
            upload_url,
            data=body,
            headers={"Authorization": auth, "Content-Type": content_type},
            timeout=120,
        )
        if uploaded.status >= 400:
            warning = f" Image skipped: {error_summary(uploaded)}."
            print(f"::warning::X media upload failed: {error_summary(uploaded)}")
        else:
            data = parse_json(uploaded) or {}
            media_id = str(data.get("media_id_string") or data.get("media_id") or "")
            if media_id:
                media_ids.append(media_id)
            else:
                warning = " Image skipped: upload response had no media id."
    payload: dict[str, object] = {"text": text}
    if media_ids:
        payload["media"] = {"media_ids": media_ids}
    tweet_url = "https://api.x.com/2/tweets"
    auth, _signature = oauth1_sign("POST", tweet_url, consumer_key, consumer_secret, token, token_secret)
    result = http_request(
        "POST",
        tweet_url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    data = require_ok(result, "X")
    tweet_id = str((data.get("data") or {}).get("id") or "")
    if not tweet_id:
        raise ApiError("X post finished without a tweet id")
    attached = " with image" if media_ids else ""
    return Outcome("ok", f"X post published (id {tweet_id}){attached}.{warning}".rstrip())


def post_pinterest() -> Outcome:
    missing = missing_secrets(["PINTEREST_ACCESS_TOKEN", "PINTEREST_BOARD_ID"])
    if missing:
        return Outcome("failed", missing_message(missing))
    package, _path = load_package()
    title = pinterest_title(package)
    description = pinterest_description(package)
    link = first_link(package)
    pin = find_media("pin.jpg")
    image_url = os.environ.get("MEDIA_IMAGE_URL", "").strip()
    if pin is not None:
        encoded = base64.b64encode(pin.read_bytes()).decode()
        media_source = {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": encoded,
        }
        source_note = "generated pin image"
    elif image_url:
        media_source = {"source_type": "image_url", "url": image_url}
        source_note = "MEDIA_IMAGE_URL"
    else:
        return Outcome(
            "failed",
            "Pinterest needs build/social/pin.jpg from prepare-media, or the MEDIA_IMAGE_URL secret.",
        )
    payload: dict[str, object] = {
        "board_id": os.environ["PINTEREST_BOARD_ID"].strip(),
        "title": title,
        "description": description,
        "alt_text": pinterest_alt(package),
        "media_source": media_source,
    }
    if link:
        payload["link"] = link
    result = http_request(
        "POST",
        "https://api.pinterest.com/v5/pins",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['PINTEREST_ACCESS_TOKEN'].strip()}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    data = require_ok(result, "Pinterest", ok=(200, 201))
    pin_id = str(data.get("id") or "")
    if not pin_id:
        raise ApiError("Pinterest create finished without a pin id")
    return Outcome("ok", f"Pinterest pin published (id {pin_id}) from {source_note}")


def font_file(name: str) -> str:
    candidates = [
        pathlib.Path("/usr/share/fonts/truetype/dejavu") / name,
        pathlib.Path("/usr/share/fonts/dejavu") / name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError(f"Font {name} not found. Install fonts-dejavu-core.")


def run_ffmpeg(args: list[str]) -> None:
    process = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "ffmpeg failed").strip()
        raise RuntimeError(detail[-2000:])


def probe_media(path: pathlib.Path) -> dict[str, object]:
    process = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError((process.stderr or "ffprobe failed")[-1000:])
    data = json.loads(process.stdout)
    video = next(stream for stream in data["streams"] if stream.get("codec_type") == "video")
    audio = [stream for stream in data["streams"] if stream.get("codec_type") == "audio"]
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "duration": float(data["format"]["duration"]),
        "video_codec": video.get("codec_name"),
        "has_audio": bool(audio),
    }


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if len(trial) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def first_sentence(text: str, limit: int = 220) -> str:
    flat = " ".join(text.split())
    match = re.search(r"^(.{20,220}?[.!?])(?:\s|$)", flat)
    sentence = match.group(1) if match else flat
    return clip(sentence, limit)


def lines_for_card(text: str, width: int, max_lines: int) -> list[str]:
    lines = wrap_text(text, width)
    if len(lines) <= max_lines:
        return lines
    budget = max(8, width * max_lines - 2)
    clipped = clip(text, budget)
    fitted = wrap_text(clipped, width)[:max_lines]
    if fitted and not fitted[-1].endswith("…"):
        last = fitted[-1]
        fitted[-1] = (last[:-1] + "…") if len(last) > 1 else "…"
    return fitted


def drawtext_filter(line_dir: pathlib.Path, lines: list[tuple[str, str, int, str, int]]) -> str:
    filters = [
        "drawbox=x=0:y=0:w=iw:h=18:color=0xD4A017:t=fill",
        "drawbox=x=0:y=ih-18:w=iw:h=18:color=0xD4A017:t=fill",
    ]
    line_dir.mkdir(parents=True, exist_ok=True)
    for index, (text, font, size, color, ypos) in enumerate(lines):
        path = line_dir / f"line-{index}.txt"
        path.write_text(text.replace("%", "%%"), encoding="utf-8")
        rendered = str(path)
        if any(token in rendered for token in (":", ",", "'", "[", "]")):
            raise RuntimeError(f"Unsafe drawtext path: {rendered}")
        filters.append(
            "drawtext="
            f"fontfile={font}:textfile={rendered}:fontsize={size}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={ypos}:fix_bounds=1"
        )
    return ",".join(filters)


def card_spec(kind: str, package: Package, story: Story | None, width: int, height: int) -> list[tuple[str, str, int, str, int]]:
    bold = font_file("DejaVuSans-Bold.ttf")
    regular = font_file("DejaVuSans.ttf")
    title_size = max(36, int(height * 0.042))
    body_size = max(24, int(height * 0.026))
    kicker_size = max(22, int(height * 0.022))
    title_width = max(12, int((width - 160) / (title_size * 0.58)))
    body_width = max(16, int((width - 160) / (body_size * 0.55)))
    lines: list[tuple[str, str, int, str, int]] = []

    def add(text: str, font: str, size: int, color: str, ypos: int) -> None:
        if text.strip():
            lines.append((text, font, size, color, ypos))

    if kind == "intro":
        y = int(height * 0.36)
        add("CENTRAL PA REPORT", bold, int(height * 0.038), GOLD, y)
        y += int(height * 0.08)
        add("Daily briefing", regular, title_size, "white", y)
        y += int(height * 0.08)
        shown_date = re.sub(r"\s*\([^)]*\)\s*$", "", package.date_line).strip() or "Central Pennsylvania"
        for row in lines_for_card(shown_date, body_width, 2):
            add(row, regular, body_size, BODY_COLOR, y)
            y += int(height * 0.04)
        count = len(package.stories)
        label = f"{count} {'story' if count == 1 else 'stories'}" if count else "Today's notes"
        add(label, regular, body_size, GOLD, y + int(height * 0.02))
        return lines
    if kind == "outro":
        y = int(height * 0.36)
        add("Full stories", bold, title_size, "white", y)
        y += int(height * 0.09)
        add("centralpareport.com", bold, body_size, GOLD, y)
        y += int(height * 0.08)
        add("Central PA Report", regular, body_size, BODY_COLOR, y)
        y += int(height * 0.05)
        add("Partnered with Real Brokerage", regular, kicker_size, BODY_COLOR, y)
        return lines
    assert story is not None
    y = int(height * 0.22)
    add("CENTRAL PA REPORT", bold, kicker_size, GOLD, y)
    y += int(height * 0.08)
    for row in wrap_text(story.hook, title_width)[:4]:
        add(row, bold, title_size, "white", y)
        y += int(title_size * 1.25)
    y += int(height * 0.03)
    source = story.facebook or story.instagram or story.title
    for row in lines_for_card(first_sentence(source), body_width, 4):
        add(row, regular, body_size, BODY_COLOR, y)
        y += int(body_size * 1.35)
    add("centralpareport.com", regular, kicker_size, GOLD, int(height * 0.86))
    return lines


def render_card_video(out: pathlib.Path, vf: str, width: int, height: int, duration: float) -> None:
    run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={BG_COLOR}:s={width}x{height}:r=30",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            f"{duration:.2f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )


def render_card_image(out: pathlib.Path, vf: str, width: int, height: int) -> None:
    run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={BG_COLOR}:s={width}x{height}:r=30",
            "-frames:v",
            "1",
            "-vf",
            vf,
            "-q:v",
            "2",
            str(out),
        ]
    )


def story_duration(count: int) -> float:
    if count <= 0:
        return 8.0
    room = MAX_SHORT_SECONDS - INTRO_SECONDS - OUTRO_SECONDS - 1
    return max(3.0, min(5.0, room / count))


def render_short(package: Package, outdir: pathlib.Path) -> dict[str, object]:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required. The workflow installs them with apt.")
    outdir.mkdir(parents=True, exist_ok=True)
    parts = outdir / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    segments: list[pathlib.Path] = []
    cards: list[tuple[str, Story | None, float]] = [("intro", None, INTRO_SECONDS)]
    per_story = story_duration(len(package.stories))
    if package.stories:
        cards.extend(("story", story, per_story) for story in package.stories)
    else:
        cards.append(("intro", None, 8.0))
    cards.append(("outro", None, OUTRO_SECONDS))
    for index, (kind, story, duration) in enumerate(cards):
        line_dir = parts / f"card-{index}"
        vf = drawtext_filter(line_dir, card_spec(kind, package, story, 1080, 1920))
        segment = parts / f"segment-{index:02d}.mp4"
        render_card_video(segment, vf, 1080, 1920, duration)
        segments.append(segment)
    concat_list = parts / "concat.txt"
    concat_list.write_text("".join(f"file '{segment.resolve()}'\n" for segment in segments), encoding="utf-8")
    video_path = outdir / "short.mp4"
    run_ffmpeg(
        [
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    )
    featured = package.stories[0] if package.stories else None
    pin_vf = drawtext_filter(parts / "pin", card_spec("story" if featured else "intro", package, featured, 1000, 1500))
    pin_path = outdir / "pin.jpg"
    render_card_image(pin_path, pin_vf, 1000, 1500)
    info = probe_media(video_path)
    if info["width"] != 1080 or info["height"] != 1920:
        raise RuntimeError(f"Rendered video is {info['width']}x{info['height']}, expected 1080x1920")
    if not info["has_audio"]:
        raise RuntimeError("Rendered video has no audio track")
    if not 3 <= float(info["duration"]) <= MAX_SHORT_SECONDS:
        raise RuntimeError(f"Rendered video duration {float(info['duration']):.1f}s is outside 3–60s")
    if info["video_codec"] != "h264":
        raise RuntimeError(f"Rendered video codec is {info['video_codec']}, expected h264")
    info["video"] = str(video_path)
    info["pin"] = str(pin_path)
    return info


def cmd_validate() -> int:
    try:
        package, path = load_package()
    except FileNotFoundError as exc:
        message = (
            f"Content file not found: {exc}. "
            f"Set CONTENT_FILE or add {DEFAULT_CONTENT_FILE} at the repo root."
        )
        print(f"::error::{message}")
        write_outputs("failed", message)
        return 1
    except RuntimeError as exc:
        print(f"::error::{exc}")
        write_outputs("failed", str(exc))
        return 1
    message = f"Content file OK: {path} ({path.stat().st_size} bytes, {len(package.stories)} stories)"
    print(message)
    for index, story in enumerate(package.stories, start=1):
        print(f"  story {index}: {story.hook}")
    write_outputs("ok", message)
    return 0


def cmd_prepare() -> int:
    try:
        package, path = load_package()
        print(f"Rendering short from {path}")
        info = render_short(package, media_dir())
    except (FileNotFoundError, RuntimeError, ApiError) as exc:
        message = scrub(str(exc))
        print(f"::error::{message}")
        write_outputs("failed", message)
        return 1
    message = (
        f"Rendered {info['width']}x{info['height']} short "
        f"({float(info['duration']):.1f}s) and a 1000x1500 pin image"
    )
    write_outputs("ok", message)
    return 0


def cmd_post(platform: str) -> int:
    posters = {
        "instagram": post_instagram,
        "facebook": post_facebook,
        "linkedin": post_linkedin,
        "youtube": post_youtube,
        "tiktok": post_tiktok,
        "x": post_x,
        "pinterest": post_pinterest,
    }
    if platform not in posters:
        write_outputs("failed", f"Unknown platform {platform}")
        return 1
    try:
        outcome = posters[platform]()
    except ApiError as exc:
        outcome = Outcome("failed", scrub(str(exc)))
    except FileNotFoundError as exc:
        outcome = Outcome("failed", f"Content file not found: {exc}")
    except Exception as exc:
        print(scrub(traceback.format_exc()), file=sys.stderr)
        outcome = Outcome("failed", scrub(str(exc) or exc.__class__.__name__))
    if outcome.status == "failed":
        print(f"::error::{outcome.detail}")
    elif outcome.status == "skipped":
        print(f"::warning::{outcome.detail}")
    write_outputs(outcome.status, outcome.detail)
    return 0 if outcome.status in {"ok", "skipped"} else 1


def classify(name: str, result: str, status: str, validate_result: str, prepare_result: str) -> str:
    if result == "success":
        if status == "skipped":
            return "skipped"
        if status == "failed":
            return "failed"
        return "ok"
    if result == "failure" or result == "cancelled":
        return "failed"
    if result == "skipped":
        if validate_result != "success":
            return "failed"
        if name in VIDEO_PLATFORMS and prepare_result != "success":
            return "failed"
        return "skipped"
    return "failed"


def summarize(env: dict[str, str]) -> tuple[int, list[tuple[str, str, str]]]:
    validate_result = env.get("VALIDATE_RESULT", "")
    prepare_result = env.get("PREPARE_RESULT", "")
    rows: list[tuple[str, str, str]] = [
        ("validate", "ok" if validate_result == "success" else "failed", env.get("VALIDATE_DETAIL", "")),
        ("prepare-media", "ok" if prepare_result == "success" else "failed", env.get("PREPARE_DETAIL", "")),
    ]
    failures: list[str] = []
    if validate_result != "success":
        failures.append("validate")
    if prepare_result != "success":
        failures.append("prepare-media")
    for name in PLATFORMS:
        result = env.get(f"RESULT_{name.upper()}", "")
        status = env.get(f"STATUS_{name.upper()}", "")
        detail = env.get(f"DETAIL_{name.upper()}", "")
        kind = classify(name, result, status, validate_result, prepare_result)
        if kind == "failed" and not detail:
            if validate_result != "success":
                detail = "Content file validation failed, so this platform did not post."
            elif name in VIDEO_PLATFORMS and prepare_result != "success":
                detail = "Video render failed, so this platform did not post."
            else:
                detail = f"Job result: {result or 'missing'}"
        rows.append((PLATFORM_LABELS[name], kind, detail))
        if kind == "failed":
            failures.append(PLATFORM_LABELS[name])
    platform_failed = any(name in PLATFORM_LABELS.values() for name in failures)
    validate_failed = validate_result != "success"
    return (1 if platform_failed or validate_failed else 0), rows


def cmd_summarize() -> int:
    code, rows = summarize(dict(os.environ))
    print(f"{'platform':<16} {'result':<10} detail")
    failed_platforms = []
    for name, kind, detail in rows:
        print(f"{name:<16} {kind:<10} {detail}")
        if kind == "failed" and name in PLATFORM_LABELS.values():
            failed_platforms.append(name)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("| Platform | Result | Detail |\n| --- | --- | --- |\n")
            for name, kind, detail in rows:
                safe_detail = detail.replace("|", "\\|")
                handle.write(f"| {name} | {kind} | {safe_detail} |\n")
    if failed_platforms:
        message = "Platforms failed: " + ", ".join(failed_platforms)
        print(f"::error::{message}")
        return 1
    if code != 0:
        print("::error::Content file validation failed.")
        return 1
    skipped = [name for name, kind, _detail in rows if kind == "skipped"]
    if skipped:
        print("Finished. Skipped: " + ", ".join(skipped))
    else:
        print("All platforms posted.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        print(
            "Usage: auto_post.py validate | prepare | post <platform> | summarize\n"
            f"Platforms: {', '.join(PLATFORMS)}"
        )
        return 0 if len(argv) > 1 else 1
    command = argv[1]
    if command == "validate":
        return cmd_validate()
    if command == "prepare":
        return cmd_prepare()
    if command == "post":
        if len(argv) < 3:
            print("Usage: auto_post.py post <platform>", file=sys.stderr)
            return 1
        return cmd_post(argv[2])
    if command == "summarize":
        return cmd_summarize()
    print(f"Unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
