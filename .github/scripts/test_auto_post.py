#!/usr/bin/env python3
"""Local checks for caption extraction, signing, and the rendered short. No network."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import auto_post

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE_PATH = ROOT / "social-media-package-2026-11-04.md"


def test_oauth_signature() -> None:
    header, signature = auto_post.oauth1_sign(
        "POST",
        "https://api.twitter.com/1.1/statuses/update.json",
        "xvz1evFS4wEEPTGEFPHBog",
        "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
        "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
        "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE",
        extra_params={
            "include_entities": "true",
            "status": "Hello Ladies + Gentlemen, a signed OAuth request!",
        },
        nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg",
        timestamp="1318622958",
    )
    assert signature == "hCtSmYh+iHYCEqBWrE7C7hYmtUk=", signature
    assert header.startswith("OAuth ")
    assert "oauth_signature" in header


def test_package_captions() -> None:
    package = auto_post.parse_package(PACKAGE_PATH.read_text(encoding="utf-8"))
    assert len(package.stories) == 4
    assert "Tallest Tower" in package.stories[0].hook
    assert package.stories[0].url.endswith("/mosaic-tallest-tower-lancaster")
    facebook = auto_post.facebook_caption(package)
    instagram = auto_post.instagram_caption(package)
    linkedin = auto_post.linkedin_text(package)
    tweet = auto_post.x_text(package)
    title = auto_post.youtube_title(package)
    description = auto_post.youtube_description(package)
    pin_title = auto_post.pinterest_title(package)
    pin_body = auto_post.pinterest_description(package)
    for label, text, limit in (
        ("facebook", facebook, auto_post.LIMIT_FACEBOOK),
        ("instagram", instagram, auto_post.LIMIT_INSTAGRAM),
        ("linkedin", linkedin, auto_post.LIMIT_LINKEDIN),
        ("x", tweet, auto_post.LIMIT_X),
        ("youtube title", title, auto_post.LIMIT_YOUTUBE_TITLE),
        ("youtube description", description, auto_post.LIMIT_YOUTUBE_DESCRIPTION),
        ("pinterest title", pin_title, auto_post.LIMIT_PINTEREST_TITLE),
        ("pinterest description", pin_body, auto_post.LIMIT_PINTEREST_DESCRIPTION),
    ):
        assert len(text) <= limit, f"{label} is {len(text)} > {limit}"
        assert "DRAFT ONLY" not in text
        assert "Pitch to" not in text
        assert "do not post" not in text.lower()
    assert "centralpareport.com" in facebook
    assert package.stories[0].url in tweet
    for story in package.stories:
        assert story.url in linkedin
    assert title.endswith(" #Shorts")
    assert "#Shorts" in description
    assert not __import__("re").search(r"(?<!\\)#", linkedin)
    long_text, truncated = auto_post.truncate("word " * 100, 40)
    assert truncated and len(long_text) <= 40 and long_text.endswith("[truncated]")
    chunks, chunk_size = auto_post.plan_tiktok_chunks(1000)
    assert chunks == [(0, 1000)] and chunk_size == 1000
    big = 70 * 1024 * 1024
    ranges, size = auto_post.plan_tiktok_chunks(big)
    assert ranges[0][0] == 0 and ranges[-1][1] == big and size == 10 * 1024 * 1024
    print(f"captions ok: fb={len(facebook)} ig={len(instagram)} li={len(linkedin)} x={len(tweet)}")


def test_missing_secrets_do_not_call_network() -> None:
    saved = os.environ.copy()
    try:
        for name in auto_post.SECRET_NAMES:
            os.environ.pop(name, None)
        os.environ["CONTENT_FILE"] = str(PACKAGE_PATH.relative_to(ROOT))
        outcome = auto_post.post_facebook()
        assert outcome.status == "failed"
        assert "FACEBOOK_ACCESS_TOKEN" in outcome.detail
        assert "FACEBOOK_PAGE_ID" in outcome.detail
        linkedin = auto_post.post_linkedin()
        assert linkedin.status == "failed" and "LINKEDIN_ACCESS_TOKEN" in linkedin.detail
    finally:
        os.environ.clear()
        os.environ.update(saved)


def test_summarize_isolates_failures() -> None:
    env = {
        "VALIDATE_RESULT": "success",
        "VALIDATE_DETAIL": "ok",
        "PREPARE_RESULT": "failure",
        "PREPARE_DETAIL": "ffmpeg failed",
    }
    for name in auto_post.PLATFORMS:
        env[f"RESULT_{name.upper()}"] = "success"
        env[f"STATUS_{name.upper()}"] = "ok"
        env[f"DETAIL_{name.upper()}"] = "posted"
    env["RESULT_YOUTUBE"] = "skipped"
    env["STATUS_YOUTUBE"] = ""
    env["DETAIL_YOUTUBE"] = ""
    env["RESULT_TIKTOK"] = "skipped"
    env["STATUS_TIKTOK"] = ""
    env["DETAIL_TIKTOK"] = ""
    env["RESULT_INSTAGRAM"] = "success"
    env["STATUS_INSTAGRAM"] = "skipped"
    env["DETAIL_INSTAGRAM"] = "no media"
    code, rows = auto_post.summarize(env)
    kinds = {name: kind for name, kind, _detail in rows}
    assert code == 1
    assert kinds["YouTube"] == "failed"
    assert kinds["TikTok"] == "failed"
    assert kinds["Facebook"] == "ok"
    assert kinds["Instagram"] == "skipped"
    assert "did not post" in dict((name, detail) for name, _kind, detail in rows)["YouTube"]


def test_render_short() -> None:
    package = auto_post.parse_package(PACKAGE_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="cpa-short-") as tmp:
        info = auto_post.render_short(package, pathlib.Path(tmp))
        assert info["width"] == 1080 and info["height"] == 1920
        assert info["has_audio"] and info["video_codec"] == "h264"
        assert 3 <= float(info["duration"]) <= 60
        pin = pathlib.Path(str(info["pin"]))
        assert pin.is_file() and pin.stat().st_size > 1000
        frame = pathlib.Path("/tmp/cpa-story-frame.jpg")
        intro = pathlib.Path("/tmp/cpa-intro-frame.jpg")
        pin_copy = pathlib.Path("/tmp/cpa-pin.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(info["video"]), "-ss", "7", "-frames:v", "1", str(frame)],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(info["video"]), "-ss", "1", "-frames:v", "1", str(intro)],
            check=True,
        )
        pin_copy.write_bytes(pin.read_bytes())
        print(f"rendered {float(info['duration']):.1f}s -> {frame} {intro} {pin_copy}")


def test_invalid_content_path() -> None:
    saved = os.environ.get("CONTENT_FILE")
    os.environ["CONTENT_FILE"] = "../secret.md"
    try:
        try:
            auto_post.content_file()
        except RuntimeError as exc:
            assert "repo-relative" in str(exc)
        else:
            raise AssertionError("absolute traversal was accepted")
    finally:
        if saved is None:
            os.environ.pop("CONTENT_FILE", None)
        else:
            os.environ["CONTENT_FILE"] = saved


def main() -> int:
    os.chdir(ROOT)
    test_oauth_signature()
    test_package_captions()
    test_missing_secrets_do_not_call_network()
    test_summarize_isolates_failures()
    test_invalid_content_path()
    test_render_short()
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
