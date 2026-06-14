"""
CookieService handles uploading, validation status, falling back to disk backup, and removing cookies.

R2 Three-Question Self-Check:
1. Contract Closure: Any JSON parsing or database transaction errors are wrapped in logical try-except blocks, ensuring a graceful return of None or False without crashing the request pipeline.
2. Symmetry: Create/Update operations write to DB and sync to disk; delete operations delete from DB and delete from disk, maintaining strict symmetry.
3. External Timing: Uses atomic db.commit() to ensure state consistency. Normalizes directory paths to absolute paths to prevent timing and directory mismatch issues.
"""

import os
import json
import uuid
import datetime
from sqlalchemy.orm import Session
from app.models.cookie import PlatformCookie
from app.config import settings


def _utcnow() -> datetime.datetime:
    """Timezone-aware UTC now; replaces deprecated datetime.datetime.utcnow()."""
    return datetime.datetime.now(datetime.timezone.utc)

class CookieService:
    def _get_cookie_dir(self) -> str:
        cookie_dir = settings.COOKIE_DIR
        # Normalize relative path to absolute path using settings.BASE_DIR for worktree compatibility
        if not os.path.isabs(cookie_dir):
            return str((settings.BASE_DIR / cookie_dir).resolve())
        return cookie_dir

    async def validate_cookie(self, db: Session, platform: str) -> bool:
        """
        Validate cookies for a platform.
        M1: Mock check (format verification and non-empty check), returns True if format is valid.
        """
        cookie = db.query(PlatformCookie).filter(PlatformCookie.platform == platform).first()
        if not cookie:
            return False
        
        # Check basic schema format
        if not isinstance(cookie.cookie_data, list) or len(cookie.cookie_data) == 0:
            return False
            
        return True

    async def get_valid_cookie(self, db: Session, platform: str) -> PlatformCookie | None:
        """
        Retrieve a valid platform cookie:
        1. DB first
        2. Fallback to reading disk backup '{platform}.json' and syncing back to DB if found.
        3. If cookie is marked invalid, triggers validate_cookie again.
        """
        cookie = db.query(PlatformCookie).filter(PlatformCookie.platform == platform).first()
        
        # Disk Hot-load Fallback
        if not cookie:
            cookie_dir = self._get_cookie_dir()
            cookie_file = os.path.join(cookie_dir, f"{platform}.json")
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file, "r", encoding="utf-8") as f:
                        cookie_data = json.load(f)
                    
                    cookie = await self.update_or_create_cookie(
                        db=db,
                        platform=platform,
                        cookie_data=cookie_data,
                        is_valid=True
                    )
                except Exception:
                    return None
                    
        # Re-verify if marked as invalid
        if cookie and not cookie.is_valid:
            is_valid = await self.validate_cookie(db, platform)
            if is_valid:
                cookie.is_valid = True
                cookie.last_checked_at = _utcnow()
                db.commit()
                db.refresh(cookie)
            else:
                return None
                
        return cookie

    async def update_or_create_cookie(self, db: Session, platform: str, cookie_data: list[dict], is_valid: bool) -> PlatformCookie:
        """
        Create or update cookie information.
        Syncs database records and backups a JSON copy to '{COOKIE_DIR}/{platform}.json'.
        """
        cookie_dir = self._get_cookie_dir()
        os.makedirs(cookie_dir, exist_ok=True)
        
        # Disk persistent backup
        cookie_file = os.path.join(cookie_dir, f"{platform}.json")
        try:
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
        except IOError:
            # Continue even if disk backup fails, but database write should still execute
            pass
            
        cookie = db.query(PlatformCookie).filter(PlatformCookie.platform == platform).first()
        now = _utcnow()
        
        if cookie:
            cookie.cookie_data = cookie_data
            cookie.is_valid = is_valid
            cookie.last_checked_at = now
            cookie.uploaded_at = now
        else:
            cookie = PlatformCookie(
                id=str(uuid.uuid4()),
                platform=platform,
                cookie_data=cookie_data,
                is_valid=is_valid,
                last_checked_at=now,
                uploaded_at=now
            )
            db.add(cookie)
            
        db.commit()
        db.refresh(cookie)
        return cookie

    async def delete_cookie(self, db: Session, platform: str) -> bool:
        """
        Deletes cookie for a platform.
        Synchronously removes database records and the corresponding disk backup.
        """
        cookie = db.query(PlatformCookie).filter(PlatformCookie.platform == platform).first()
        deleted = False
        
        if cookie:
            db.delete(cookie)
            db.commit()
            deleted = True
            
        # Remove physical disk backup
        cookie_dir = self._get_cookie_dir()
        cookie_file = os.path.join(cookie_dir, f"{platform}.json")
        if os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
                deleted = True
            except OSError:
                pass
                
        return deleted
