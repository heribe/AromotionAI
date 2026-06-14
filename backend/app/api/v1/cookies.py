"""
Cookie API endpoints handler (Upload, Status, Delete).

R2 Three-Question Self-Check:
1. Contract Closure: Checks platform compatibility, ensures valid uploaded JSON schema, and raises clean 400/404 HTTP exceptions.
2. Symmetry: Symmetric interface endpoints provided (post upload, get status, delete).
3. External Timing: Async non-blocking file reads (await file.read()) used to handle cookie data uploads smoothly.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.cookie import PlatformCookie
from app.schemas.common import BaseResponse
from app.schemas.cookie import CookieUploadResponse, CookieStatusResponse, CookieStatusItem
from app.services.cookie_service import CookieService

router = APIRouter(prefix="/cookies", tags=["Cookies"])
cookie_service = CookieService()

SUPPORTED_PLATFORMS = {"douyin", "xiaohongshu", "taobao"}

@router.post("/upload", response_model=BaseResponse[CookieUploadResponse])
async def upload_cookie(
    platform: str = Form(..., description="Target social media platform"),
    file: UploadFile = File(..., description="Browser Cookie JSON format file"),
    db: Session = Depends(get_db)
):
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的平台: {platform}"
        )
        
    # Read file and validate JSON array format
    try:
        content = await file.read()
        cookie_data = json.loads(content)
        if not isinstance(cookie_data, list):
            raise ValueError("Cookie file must be a JSON array")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的 Cookie 文件格式: {str(e)}"
        )
        
    # Persistence
    cookie = await cookie_service.update_or_create_cookie(
        db=db,
        platform=platform,
        cookie_data=cookie_data,
        is_valid=True
    )
    
    return BaseResponse(
        code=0,
        message="success",
        data=CookieUploadResponse(
            platform=cookie.platform,
            is_valid=cookie.is_valid,
            uploaded_at=cookie.uploaded_at
        )
    )

@router.get("/status", response_model=BaseResponse[CookieStatusResponse])
async def get_cookie_status(db: Session = Depends(get_db)):
    """返回所有支持平台的 Cookie 状态。

    直接查询 DB（只读、幂等），不调用 get_valid_cookie 以避免触发磁盘热加载
    或重新校验等副作用。未配置的平台也列出，标记 is_valid=False 且时间戳为 None。
    """
    # 预加载所有已配置平台记录，避免 N 次查询
    configured = {
        c.platform: c
        for c in db.query(PlatformCookie).all()
    }

    cookies_status = []
    for platform in SUPPORTED_PLATFORMS:
        cookie = configured.get(platform)
        if cookie:
            cookies_status.append(
                CookieStatusItem(
                    platform=cookie.platform,
                    is_valid=cookie.is_valid,
                    uploaded_at=cookie.uploaded_at,
                    last_checked_at=cookie.last_checked_at
                )
            )
        else:
            cookies_status.append(
                CookieStatusItem(
                    platform=platform,
                    is_valid=False,
                    uploaded_at=None,
                    last_checked_at=None
                )
            )

    return BaseResponse(
        code=0,
        message="success",
        data=CookieStatusResponse(cookies=cookies_status)
    )

@router.delete("/{platform}", response_model=BaseResponse[dict])
async def delete_cookie(platform: str, db: Session = Depends(get_db)):
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的平台: {platform}"
        )
        
    deleted = await cookie_service.delete_cookie(db, platform)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"平台 {platform} 的 Cookie 配置不存在"
        )
        
    return BaseResponse(
        code=0,
        message="success",
        data={"platform": platform, "deleted": True}
    )
