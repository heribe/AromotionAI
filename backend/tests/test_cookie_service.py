"""
CookieService direct unit tests.

These tests bypass the HTTP API layer and exercise CookieService directly,
covering the contract branches that test_cookies.py (API-level) does not reach:
  - update_or_create_cookie: create path vs update path (uploaded_at refreshed)
  - get_valid_cookie: disk hot-load fallback (DB empty, disk file present)
  - get_valid_cookie: re-validate when is_valid=False
  - validate_cookie: empty / non-list / valid formats
  - delete_cookie: symmetric DB + disk removal

R2 Three-Question Self-Check:
1. Contract Closure: Each branch of the documented CookieService contract
   (validate / get_valid / update_or_create / delete) is exercised with both
   happy and edge inputs.
2. Symmetry: Create + delete pairs verify DB and disk state return to empty.
3. External Timing: Uses the per-function `db` fixture from conftest.py so
   every test starts from a clean schema; disk files are written under the
   test cookie dir (settings.COOKIE_DIR overridden in conftest.py).
"""

import json
import os

import pytest

from app.config import settings
from app.models.cookie import PlatformCookie
from app.services.cookie_service import CookieService


def _cookie_dir() -> str:
    """Resolve the active cookie dir exactly as CookieService does."""
    cookie_dir = settings.COOKIE_DIR
    if not os.path.isabs(cookie_dir):
        return str((settings.BASE_DIR / cookie_dir).resolve())
    return cookie_dir


def _write_disk_cookie(platform: str, cookie_data: list) -> str:
    """Write a cookie json to the disk backup location and return its path."""
    cookie_dir = _cookie_dir()
    os.makedirs(cookie_dir, exist_ok=True)
    path = os.path.join(cookie_dir, f"{platform}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookie_data, f, ensure_ascii=False)
    return path


def _disk_cookie_exists(platform: str) -> bool:
    return os.path.exists(os.path.join(_cookie_dir(), f"{platform}.json"))


@pytest.mark.asyncio
async def test_validate_cookie_returns_false_when_missing(db):
    svc = CookieService()
    assert await svc.validate_cookie(db, "douyin") is False


@pytest.mark.asyncio
async def test_validate_cookie_rejects_non_list_data(db):
    """cookie_data stored as a dict (not a list) must be rejected by the M1 mock check."""
    svc = CookieService()
    db.add(PlatformCookie(
        id="test-1",
        platform="douyin",
        cookie_data={"sessionid": "x"},  # dict, not list -> invalid
        is_valid=True,
    ))
    db.commit()

    assert await svc.validate_cookie(db, "douyin") is False


@pytest.mark.asyncio
async def test_validate_cookie_rejects_empty_list(db):
    svc = CookieService()
    db.add(PlatformCookie(
        id="test-2",
        platform="douyin",
        cookie_data=[],  # empty list -> invalid
        is_valid=True,
    ))
    db.commit()

    assert await svc.validate_cookie(db, "douyin") is False


@pytest.mark.asyncio
async def test_validate_cookie_accepts_valid_format(db):
    svc = CookieService()
    db.add(PlatformCookie(
        id="test-3",
        platform="douyin",
        cookie_data=[{"name": "sessionid", "value": "abc"}],
        is_valid=True,
    ))
    db.commit()

    assert await svc.validate_cookie(db, "douyin") is True


@pytest.mark.asyncio
async def test_update_or_create_cookie_creates_record_and_disk_backup(db):
    svc = CookieService()
    cookie_data = [{"name": "sessionid", "value": "v1"}]

    cookie = await svc.update_or_create_cookie(db, "douyin", cookie_data, is_valid=True)

    # DB record
    assert cookie.id is not None
    assert cookie.platform == "douyin"
    assert cookie.cookie_data == cookie_data
    assert cookie.is_valid is True
    assert cookie.uploaded_at is not None

    # Disk backup symmetric with the DB write
    assert _disk_cookie_exists("douyin")
    with open(os.path.join(_cookie_dir(), "douyin.json"), encoding="utf-8") as f:
        assert json.load(f) == cookie_data


@pytest.mark.asyncio
async def test_update_or_create_cookie_updates_existing_and_refreshes_uploaded_at(db):
    svc = CookieService()

    first = await svc.update_or_create_cookie(
        db, "douyin", [{"name": "a", "value": "1"}], is_valid=True
    )
    first_uploaded_at = first.uploaded_at

    # Second call with the same platform must update in place (unique platform).
    updated = await svc.update_or_create_cookie(
        db, "douyin", [{"name": "b", "value": "2"}], is_valid=False
    )

    assert updated.id == first.id  # same row, not a new one
    assert updated.cookie_data == [{"name": "b", "value": "2"}]
    assert updated.is_valid is False
    assert updated.uploaded_at >= first_uploaded_at

    # Only one DB row for the platform.
    assert db.query(PlatformCookie).filter_by(platform="douyin").count() == 1


@pytest.mark.asyncio
async def test_get_valid_cookie_returns_none_when_missing_everywhere(db):
    svc = CookieService()
    # Ensure no leftover disk file from other tests (isolation).
    disk_path = os.path.join(_cookie_dir(), "douyin.json")
    if os.path.exists(disk_path):
        os.remove(disk_path)
    # No DB record, no disk file -> None.
    assert await svc.get_valid_cookie(db, "douyin") is None


@pytest.mark.asyncio
async def test_get_valid_cookie_disk_hot_load_fallback(db):
    """Core M1 contract: DB empty but disk backup present -> sync back to DB."""
    svc = CookieService()
    disk_data = [{"name": "sessionid", "value": "from-disk"}]
    _write_disk_cookie("douyin", disk_data)

    # Sanity: no DB row yet.
    assert db.query(PlatformCookie).filter_by(platform="douyin").first() is None

    cookie = await svc.get_valid_cookie(db, "douyin")

    # Disk file was hot-loaded and persisted into DB.
    assert cookie is not None
    assert cookie.cookie_data == disk_data
    assert cookie.is_valid is True
    assert db.query(PlatformCookie).filter_by(platform="douyin").count() == 1


@pytest.mark.asyncio
async def test_get_valid_cookie_revalidates_when_marked_invalid(db):
    """When a cookie row exists but is_valid=False, get_valid_cookie re-runs validate_cookie."""
    svc = CookieService()
    # A structurally valid cookie but flagged invalid.
    await svc.update_or_create_cookie(
        db, "douyin", [{"name": "x", "value": "y"}], is_valid=False
    )
    row = db.query(PlatformCookie).filter_by(platform="douyin").first()
    assert row.is_valid is False

    cookie = await svc.get_valid_cookie(db, "douyin")

    # M1 mock validate_cookie inspects format (valid list) -> re-marks valid.
    assert cookie is not None
    assert cookie.is_valid is True


@pytest.mark.asyncio
async def test_get_valid_cookie_returns_none_when_invalid_and_unfixable(db):
    """Cookie flagged invalid AND structurally invalid -> None after failed re-validation."""
    svc = CookieService()
    db.add(PlatformCookie(
        id="bad-1",
        platform="douyin",
        cookie_data=[],  # empty list -> validate returns False
        is_valid=False,
    ))
    db.commit()

    assert await svc.get_valid_cookie(db, "douyin") is None


@pytest.mark.asyncio
async def test_delete_cookie_removes_db_and_disk_symmetrically(db):
    svc = CookieService()
    await svc.update_or_create_cookie(
        db, "douyin", [{"name": "a", "value": "1"}], is_valid=True
    )
    assert db.query(PlatformCookie).filter_by(platform="douyin").first() is not None
    assert _disk_cookie_exists("douyin")

    deleted = await svc.delete_cookie(db, "douyin")

    assert deleted is True
    assert db.query(PlatformCookie).filter_by(platform="douyin").first() is None
    assert not _disk_cookie_exists("douyin")


@pytest.mark.asyncio
async def test_delete_cookie_returns_false_when_nothing_exists(db):
    svc = CookieService()
    # No DB row, no disk file.
    deleted = await svc.delete_cookie(db, "douyin")
    assert deleted is False


@pytest.mark.asyncio
async def test_get_cookie_dir_resolves_relative_to_base_dir():
    """Worktree compatibility: a relative COOKIE_DIR is resolved to an absolute path
    rooted at settings.BASE_DIR. In the test conftest COOKIE_DIR is already absolute,
    so we verify the resolution logic by feeding a synthetic relative value."""
    svc = CookieService()

    # 1. When COOKIE_DIR is already absolute, it is returned unchanged.
    abs_dir = os.path.join(str(settings.BASE_DIR), "custom_cookies_abs")
    original = settings.COOKIE_DIR
    try:
        settings.COOKIE_DIR = abs_dir
        assert svc._get_cookie_dir() == abs_dir

        # 2. When COOKIE_DIR is relative, it is joined onto BASE_DIR.
        settings.COOKIE_DIR = "custom_cookies_rel"
        resolved = svc._get_cookie_dir()
        assert os.path.isabs(resolved)
        assert resolved.endswith("custom_cookies_rel")
    finally:
        settings.COOKIE_DIR = original
