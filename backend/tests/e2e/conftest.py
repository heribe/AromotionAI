import asyncio
import json
import uuid
import pytest
from pathlib import Path
from typing import AsyncIterator
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

# --- File Path Resolution ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/tests/e2e -> backend/
MOCK_DATA_DIR = PROJECT_ROOT / "tests" / "e2e" / "mock_data"

# --- In-Memory State Mock Database ---
cookies = {}
tasks = {}
sessions = {}
chat_histories = {}

ai_routing = {
    "analysis_task": {
        "provider": "glm",
        "model": "glm-4",
        "api_key": "sk-mockglmkey",
        "endpoint": "https://api.zhipuai.cn/v1"
    },
    "fragrance_reasoning": {
        "provider": "glm",
        "model": "glm-4",
        "api_key": "sk-mockglmkey",
        "endpoint": "https://api.zhipuai.cn/v1"
    },
    "fragrance_chat": {
        "provider": "glm",
        "model": "glm-4",
        "api_key": "sk-mockglmkey",
        "endpoint": "https://api.zhipuai.cn/v1"
    }
}

lock = asyncio.Lock()

# --- Helper functions to load mock data ---
def load_mock_json(filename: str):
    path = MOCK_DATA_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Define default structures for tests to run even if not explicitly created
def reset_db_state():
    global cookies, tasks, sessions, chat_histories, ai_routing
    cookies.clear()
    tasks.clear()
    sessions.clear()
    chat_histories.clear()
    
    # Pre-populate defaults
    cookies["douyin"] = {
        "platform": "douyin",
        "is_valid": True,
        "uploaded_at": "2026-06-13T10:00:00+08:00",
        "last_checked_at": "2026-06-13T10:00:00+08:00",
        "cookie_data": [{"name": "sessionid", "value": "mocksession123"}]
    }
    
    # Reset routing to default
    ai_routing.update({
        "analysis_task": {"provider": "glm", "model": "glm-4", "api_key": "sk-mockglmkey", "endpoint": "https://api.zhipuai.cn/v1"},
        "fragrance_reasoning": {"provider": "glm", "model": "glm-4", "api_key": "sk-mockglmkey", "endpoint": "https://api.zhipuai.cn/v1"},
        "fragrance_chat": {"provider": "glm", "model": "glm-4", "api_key": "sk-mockglmkey", "endpoint": "https://api.zhipuai.cn/v1"}
    })

# Call reset initially
reset_db_state()


# --- Stub FastAPI Application ---
app = FastAPI(title="AromotionAI Stub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- F1: Cookie Management ---

@app.post("/api/v1/cookies/upload")
async def upload_cookie(platform: str = Form(...), file: UploadFile = File(...)):
    if platform not in ["douyin", "xiaohongshu", "taobao"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Cookie file is empty")
    
    try:
        cookie_data = json.loads(content.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
        
    cookies[platform] = {
        "platform": platform,
        "is_valid": True,
        "uploaded_at": "2026-06-13T10:00:00+08:00",
        "last_checked_at": "2026-06-13T10:00:00+08:00",
        "cookie_data": cookie_data
    }
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "platform": platform,
            "is_valid": True,
            "uploaded_at": "2026-06-13T10:00:00+08:00"
        }
    }

@app.get("/api/v1/cookies/status")
async def get_cookie_status(platform: str = Query(None)):
    if platform and platform not in ["douyin", "xiaohongshu", "taobao"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    # If platform is requested but does not exist, we should return empty or list
    all_platforms = ["douyin", "xiaohongshu", "taobao"]
    result_list = []
    
    for p in all_platforms:
        if p in cookies:
            result_list.append({
                "platform": p,
                "is_valid": cookies[p]["is_valid"],
                "uploaded_at": cookies[p]["uploaded_at"],
                "last_checked_at": cookies[p]["last_checked_at"]
            })
        else:
            result_list.append({
                "platform": p,
                "is_valid": False,
                "uploaded_at": None,
                "last_checked_at": None
            })
            
    if platform:
        # Filter for specific platform
        filtered = [r for r in result_list if r["platform"] == platform]
        return {"code": 0, "data": {"cookies": filtered}}
        
    return {"code": 0, "data": {"cookies": result_list}}

@app.delete("/api/v1/cookies/{platform}")
async def delete_cookie(platform: str):
    if platform not in ["douyin", "xiaohongshu", "taobao"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    if platform not in cookies:
        raise HTTPException(status_code=404, detail="Cookie not found")
    del cookies[platform]
    return {"code": 0, "message": "Cookie deleted successfully"}

@app.post("/api/v1/cookies/validate/{platform}")
async def validate_cookie(platform: str):
    if platform not in ["douyin", "xiaohongshu", "taobao"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    if platform not in cookies:
        return {"code": 0, "data": {"is_valid": False}}
    # Check if is_valid is marked false
    return {"code": 0, "data": {"is_valid": cookies[platform]["is_valid"]}}


# --- F2: Analysis Task Creation ---

@app.post("/api/v1/analysis/create")
async def create_analysis_task(payload: dict):
    blogger_url = payload.get("blogger_url")
    platform = payload.get("platform", "auto")
    analysis_level = payload.get("analysis_level", "standard")
    custom_config = payload.get("custom_config")
    
    if not blogger_url or not isinstance(blogger_url, str) or not blogger_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid blogger URL format")
        
    # Auto detect platform
    if platform == "auto" or not platform:
        if "douyin.com" in blogger_url:
            platform = "douyin"
        elif "xiaohongshu.com" in blogger_url:
            platform = "xiaohongshu"
        else:
            platform = "douyin" # Default fallback
            
    if platform not in ["douyin", "xiaohongshu", "taobao"]:
        raise HTTPException(status_code=400, detail="Platform not supported")
        
    # Check if cookie is uploaded
    if platform not in cookies or not cookies[platform]["is_valid"]:
        raise HTTPException(status_code=400, detail="Platform cookie is required and must be valid")
        
    if analysis_level == "custom":
        if not custom_config:
            raise HTTPException(status_code=400, detail="Custom configuration is required for custom analysis level")
        # Validate out-of-bounds parameters
        post_selection = custom_config.get("post_selection", {})
        top_count = post_selection.get("top_count", 0)
        recent_count = post_selection.get("recent_count", 0)
        if top_count < 0 or top_count > 100 or recent_count < 0 or recent_count > 100:
            raise HTTPException(status_code=422, detail="Parameters out of bounds")
            
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "platform": platform,
        "blogger_url": blogger_url,
        "analysis_level": analysis_level,
        "custom_config": custom_config,
        "status": "pending",
        "progress": 0,
        "current_step": "等待开始",
        "blogger_info": None,
        "created_at": "2026-06-13T10:00:00+08:00",
        "updated_at": "2026-06-13T10:00:00+08:00",
        "completed_at": None,
        "sub_steps": []
    }
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": task_id,
            "status": "pending",
            "created_at": "2026-06-13T10:00:00+08:00"
        }
    }


# --- F3: Task Progress Tracking ---

@app.get("/api/v1/analysis/{task_id}")
async def get_task_details(task_id: str):
    # Try parsing UUID to check validity
    try:
        uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid task ID format")
        
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "code": 0,
        "data": tasks[task_id]
    }

@app.post("/api/v1/analysis/{task_id}/cancel")
async def cancel_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = tasks[task_id]
    if task["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed task")
    if task["status"] in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Task is already terminated")
        
    task["status"] = "cancelled"
    task["current_step"] = "已取消"
    return {"code": 0, "message": "Task cancelled successfully"}

@app.get("/api/v1/analysis/{task_id}/progress")
async def stream_progress(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = tasks[task_id]
    
    async def event_generator():
        if task["status"] in ("completed", "failed", "cancelled"):
            if task["status"] == "completed":
                yield f"event: complete\ndata: {json.dumps({'task_id': task_id, 'report_id': task_id}, ensure_ascii=False)}\n\n"
            elif task["status"] == "failed":
                yield f"event: error\ndata: {json.dumps({'task_id': task_id, 'error': 'Task execution failed'}, ensure_ascii=False)}\n\n"
            return
            
        # Run progression
        steps = [
            {"progress": 10, "status": "collecting", "step": "正在采集博主资料", "event": "progress"},
            {"event": "step_complete", "step": "博主资料", "summary": "采集成功: 时尚博主A, 粉丝数 550000"},
            {"progress": 30, "status": "collecting", "step": "正在采集评论", "event": "progress"},
            {"progress": 50, "status": "analyzing", "step": "正在分析博主内容", "event": "progress"},
            {"progress": 80, "status": "analyzing", "step": "正在生成画像标签", "event": "progress"},
            {"progress": 100, "status": "completed", "step": "分析完成", "event": "progress"},
            {"event": "complete", "report_id": task_id}
        ]
        
        # Determine if we should fail (simulating error)
        should_fail = "fail" in task["blogger_url"]
        
        for step in steps:
            # Check for deletions
            if task_id not in tasks:
                break
            # Check for cancellation
            if task["status"] in ("failed", "cancelled"):
                break
            # Check for cookie deletion mid-run
            platform = task["platform"]
            if platform not in cookies or not cookies[platform]["is_valid"]:
                task["status"] = "failed"
                yield f"event: error\ndata: {json.dumps({'task_id': task_id, 'error': 'CookieExpiredError: Cookie missing or expired'}, ensure_ascii=False)}\n\n"
                break
                
            if should_fail and step.get("progress", 0) > 30:
                task["status"] = "failed"
                yield f"event: error\ndata: {json.dumps({'task_id': task_id, 'error': 'API network failure simulated'}, ensure_ascii=False)}\n\n"
                break
                
            if "progress" in step:
                task["progress"] = step["progress"]
                task["status"] = step["status"]
                task["current_step"] = step["step"]
                
                # Update sub_steps
                sub_steps = []
                step_names = ["博主资料", "帖子列表", "媒体下载", "评论采集", "评论者分析", "内容分析", "标签生成"]
                for i, name in enumerate(step_names):
                    if name == "博主资料" and task["progress"] >= 10:
                        status = "completed"
                    elif name == "帖子列表" and task["progress"] >= 15:
                        status = "completed"
                    elif name == "媒体下载" and task["progress"] >= 30:
                        status = "completed"
                    elif name == "评论采集" and task["progress"] >= 50:
                        status = "completed"
                    elif name == "评论者分析" and task["progress"] >= 80:
                        status = "completed"
                    elif name == "内容分析" and task["progress"] >= 85:
                        status = "completed"
                    elif name == "标签生成" and task["progress"] >= 100:
                        status = "completed"
                    else:
                        status = "running" if task["progress"] > 0 else "pending"
                    sub_steps.append({"name": name, "status": status})
                task["sub_steps"] = sub_steps
                
                data = {
                    "task_id": task_id,
                    "status": task["status"],
                    "progress": task["progress"],
                    "current_step": task["current_step"],
                    "sub_steps": task["sub_steps"]
                }
                yield f"event: progress\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            elif step["event"] == "step_complete":
                data = {
                    "step": step["step"],
                    "summary": step["summary"]
                }
                yield f"event: step_complete\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            elif step["event"] == "complete":
                task["status"] = "completed"
                task["progress"] = 100
                task["completed_at"] = "2026-06-13T10:12:00+08:00"
                # Populate blogger info from mock json
                profile_mock = load_mock_json("blogger_profile.json")
                task["blogger_info"] = {
                    "nickname": profile_mock.get("nickname", "时尚博主A"),
                    "avatar_url": profile_mock.get("avatar_url", ""),
                    "follower_count": profile_mock.get("follower_count", 550000)
                }
                data = {
                    "task_id": task_id,
                    "report_id": step["report_id"]
                }
                yield f"event: complete\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                
            await asyncio.sleep(0.01)
            
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/api/v1/analysis/list")
async def list_tasks(page: int = 1, page_size: int = 10, status: str = "all"):
    items = list(tasks.values())
    if status != "all":
        items = [i for i in items if i["status"] == status]
        
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]
    
    # Construct has_fragrance_session
    for item in paginated_items:
        # Check if there is an active fragrance session associated with this task
        sess = [s for s in sessions.values() if s["task_id"] == item["task_id"]]
        item["has_fragrance_session"] = len(sess) > 0
        
    return {
        "code": 0,
        "data": {
            "total": len(items),
            "page": page,
            "page_size": page_size,
            "items": paginated_items
        }
    }


# --- F4: Reports & Tags ---

@app.get("/api/v1/analysis/{task_id}/report")
async def get_profile_report(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task["status"] in ("pending", "collecting"):
        raise HTTPException(status_code=400, detail="Report is not generated yet")
        
    profile_mock = load_mock_json("blogger_profile.json")
    
    # Build complete report structure
    report = {
        "climate_consumption": {
            "climate_zone": {"湿热南方": 42, "干燥北方": 28, "四季分明": 30},
            "city_tier": {"一线/新一线": 35, "二线": 40, "三线及以下": 25},
            "culture_circle": {"日韩影响圈": 27, "内陆文化圈": 45, "港台风影响圈": 28},
            "concentration": "全国分散型（无区域>15%）",
            "summary": "粉丝分布全国，以内陆文化圈为主..."
        },
        "fragrance_consumption": {
            "price_tier": {"日常平价": 31, "轻奢入门": 31, "品质消费": 28, "高端消费": 10},
            "purchase_motivation": {"情绪需求": 35, "社交需求": 25, "身份需求": 20, "功能需求": 15, "收藏需求": 5},
            "decision_path": {"种草型": 40, "做功课型": 25, "冲动型": 20, "社交触发型": 15},
            "consumption_frequency": {"高频日常": 30, "场合驱动": 45, "低频尝鲜": 25},
            "summary": "以轻奢入门和日常平价为主..."
        },
        "fashion_fragrance_map": {
            "fashion_style": {"甜美系": 35, "古典系": 25, "哥特系": 15, "国潮系": 15, "日常休闲": 10},
            "fashion_scene": {"拍照出片": 30, "日常通勤": 25, "聚会活动": 25, "约会社交": 20},
            "color_preference": {"粉色系": 30, "蓝紫系": 25, "黑白系": 25, "暖色系": 20},
            "fashion_completeness": {"精致": 40, "进阶": 30, "全套": 20, "基础": 10},
            "summary": "以甜美系和古典系为主..."
        },
        "lifestyle_scenario": {
            "core_interest": {"亚文化穿搭": 23, "日常自拍": 28, "二次元": 12, "旅行风景": 15, "其他": 22},
            "social_activity": {"圈层社交": 35, "高频社交": 20, "线上为主": 30, "独处型": 15},
            "aesthetic_personality": {"冒险型": 30, "收藏型": 25, "保守型": 25, "功能型": 20},
            "fragrance_timing": {"全天": 35, "白天为主": 30, "傍晚夜间": 25, "居家为主": 10},
            "content_consumption": {"种草转化型": 35, "深度参与型": 30, "情感共鸣型": 25, "路人围观型": 10},
            "summary": "以日常自拍和亚文化穿搭为主..."
        },
        "overall_summary": "该博主的粉丝群体以年轻女性为主..."
    }
    
    return {
        "code": 0,
        "data": {
            "task_id": task_id,
            "blogger_info": {
                "nickname": profile_mock.get("nickname", "时尚博主A"),
                "avatar_url": profile_mock.get("avatar_url", ""),
                "follower_count": profile_mock.get("follower_count", 550000),
                "platform": task["platform"]
            },
            "report": report,
            "full_report_markdown": "## 博主 时尚博主A 粉丝画像\n\n### 一、气候-消费带\n...\n"
        }
    }

@app.get("/api/v1/analysis/{task_id}/tags")
async def get_aggregated_tags(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task["status"] == "failed":
        raise HTTPException(status_code=400, detail="Tags unavailable for failed tasks")
        
    dimensions = [
        {
            "dimension_id": "climate_consumption",
            "dimension_name": "气候-消费带",
            "sub_dimensions": [
                {
                    "sub_id": "climate_zone",
                    "sub_name": "气候带",
                    "tags": [
                        {"name": "湿热南方", "percentage": 42, "is_default_selected": true, "mutually_exclusive_group": "climate"},
                        {"name": "干燥北方", "percentage": 28, "is_default_selected": false, "mutually_exclusive_group": "climate"},
                        {"name": "四季分明", "percentage": 30, "is_default_selected": false, "mutually_exclusive_group": "climate"}
                    ],
                    "is_mutually_exclusive": True,
                    "max_select": 1
                },
                {
                    "sub_id": "city_tier",
                    "sub_name": "城市线级",
                    "tags": [
                        {"name": "一线/新一线", "percentage": 35, "is_default_selected": true},
                        {"name": "二线", "percentage": 40, "is_default_selected": true},
                        {"name": "三线及以下", "percentage": 25, "is_default_selected": false}
                    ],
                    "is_mutually_exclusive": False,
                    "max_select": None
                }
            ]
        },
        {
            "dimension_id": "fashion_fragrance_map",
            "dimension_name": "穿搭风格-香调映射",
            "sub_dimensions": [
                {
                    "sub_id": "fashion_style",
                    "sub_name": "穿搭风格",
                    "tags": [
                        {"name": "甜美系", "percentage": 35, "is_default_selected": true},
                        {"name": "古典系", "percentage": 25, "is_default_selected": false},
                        {"name": "哥特系", "percentage": 15, "is_default_selected": false}
                    ],
                    "is_mutually_exclusive": False,
                    "max_select": None
                }
            ]
        }
    ]
    return {
        "code": 0,
        "data": {
            "dimensions": dimensions
        }
    }

@app.delete("/api/v1/analysis/{task_id}")
async def delete_analysis_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task["status"] in ("collecting", "analyzing"):
        raise HTTPException(status_code=400, detail="Cannot delete task mid-run")
        
    del tasks[task_id]
    
    # Cascade deletes
    to_delete_sessions = [k for k, v in sessions.items() if v["task_id"] == task_id]
    for sid in to_delete_sessions:
        del sessions[sid]
        if sid in chat_histories:
            del chat_histories[sid]
            
    return {"code": 0, "message": "Task and associated media cleaned up successfully"}


# --- F5: Fragrance Recommendation ---

@app.post("/api/v1/fragrance/generate")
async def generate_fragrance(payload: dict):
    task_id = payload.get("task_id")
    selected_tags = payload.get("selected_tags")
    plan_count = payload.get("plan_count", 3)
    
    if not task_id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = tasks[task_id]
    if task["status"] == "failed":
        raise HTTPException(status_code=400, detail="Cannot generate recommendations for failed tasks")
        
    if not selected_tags:
        raise HTTPException(status_code=400, detail="At least one tag is required")
        
    # Schema validation for selected_tags (must be dictionary of dictionaries)
    if not isinstance(selected_tags, dict) or any(not isinstance(v, dict) for v in selected_tags.values()):
        raise HTTPException(status_code=422, detail="Invalid selected tags structure")
        
    if plan_count < 1 or plan_count > 10:
        raise HTTPException(status_code=422, detail="plan_count must be between 1 and 10")
        
    # Load mock plans
    rec_mock = load_mock_json("fragrance_recommendation.json")
    iceberg_mock = load_mock_json("iceberg_analysis.json")
    
    # Select plan_count recommendations
    recommendations = []
    for i in range(plan_count):
        # reuse mock plans cyclically or duplicate
        base_plan = rec_mock[i % len(rec_mock)]
        plan = base_plan.copy()
        plan["plan_id"] = f"plan_{i+1}"
        recommendations.append(plan)
        
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "session_id": session_id,
        "task_id": task_id,
        "selected_tags": selected_tags,
        "recommendations": recommendations,
        "iceberg_analysis": iceberg_mock,
        "status": "completed",
        "created_at": "2026-06-13T11:00:00+08:00"
    }
    
    # Initialize history
    chat_histories[session_id] = [
        {
            "id": "msg_initial",
            "role": "assistant",
            "content": f"根据您选择的标签，我为您生成了 {plan_count} 套香调方案。",
            "updated_plans": None,
            "created_at": "2026-06-13T11:00:00+08:00"
        }
    ]
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": "completed",
            "recommendations": recommendations
        }
    }


# --- F6: Interactive Chat ---

@app.post("/api/v1/fragrance/{session_id}/chat")
async def chat_interaction(session_id: str, payload: dict, request: Request):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Empty chat message")
        
    if "malformed_json" in message:
        raise HTTPException(status_code=502, detail="Bad gateway: malformed JSON from AI")
        
    session = sessions[session_id]
    
    # Save user message
    msg_id_user = "msg_" + str(uuid.uuid4())[:8]
    chat_histories[session_id].append({
        "id": msg_id_user,
        "role": "user",
        "content": message,
        "created_at": "2026-06-13T11:02:00+08:00"
    })
    
    # Determine changes based on user prompt
    updated_plans = None
    reply = f"收到您的反馈：'{message}'。我理解您的需求。"
    
    # Simulation logic for turns in Scenario 4 / test_f6_post_chat_message
    if "woody" in message.lower() or "沉香" in message or "乌木" in message:
        # Update plan 1 base notes to be more woody
        plan1 = session["recommendations"][0].copy()
        plan1["category"] = "花香木质调"
        plan1["base_notes"] = [
            {"name": "沉香", "description": "深沉的东方木质", "reason": "增加神秘感和深度", "changed": True},
            {"name": "乌木", "description": "烟熏的暗色木质", "reason": "与粉色系形成反差张力", "changed": True}
        ]
        plan1["recommendation_reason"] = "修改后的方案保留了花果甜美的前中调，但通过沉香和乌木的后调创造了一个戏剧性的反转..."
        session["recommendations"][0] = plan1
        updated_plans = [plan1]
        reply = "好的，我理解你希望增加方案一的深度和层次感。已将后调从白檀+香草替换为沉香+乌木..."
        
    elif "grapefruit" in message.lower() or "葡萄柚" in message:
        # Turn 1: update plan 1 top notes to Grapefruit
        plan1 = session["recommendations"][0].copy()
        plan1["top_notes"] = [
            {"name": "葡萄柚 (Grapefruit)", "description": "微酸微涩的柑橘香", "reason": "带来更多活力活力", "changed": True},
            {"name": "粉红胡椒", "description": "微辣的甜蜜点缀", "reason": "匹配甜美系风格中的俏皮元素"}
        ]
        session["recommendations"][0] = plan1
        updated_plans = [plan1]
        reply = "已为您将方案一的前调更新为葡萄柚（Grapefruit）。"
        
    elif "emotional" in message.lower() or "情绪" in message:
        # Turn 2: explain emotional benefits, no plan updates
        reply = "葡萄柚的香气含有丰富的柠檬烯，能够刺激大脑分泌多巴胺，缓解焦虑，带来积极振奋的情绪价值。"
        updated_plans = None
        
    elif "cedarwood" in message.lower() or "雪松" in message:
        # Turn 3: add Cedarwood to plan 1 base notes
        plan1 = session["recommendations"][0].copy()
        plan1["base_notes"] = [
            {"name": "雪松 (Cedarwood)", "description": "干净挺拔的木香", "reason": "提供温暖干燥的支持", "changed": True},
            {"name": "香草", "description": "甜蜜的温暖基调", "reason": "满足情绪需求中的安全感和愉悦"}
        ]
        session["recommendations"][0] = plan1
        updated_plans = [plan1]
        reply = "好的，已在方案一的后调中加入雪松。"

    msg_id_assistant = "msg_" + str(uuid.uuid4())[:8]
    chat_histories[session_id].append({
        "id": msg_id_assistant,
        "role": "assistant",
        "content": reply,
        "updated_plans": updated_plans,
        "created_at": "2026-06-13T11:02:05+08:00"
    })
    
    # Check if SSE is requested
    accept_header = request.headers.get("accept", "")
    if "text/event-stream" in accept_header:
        async def chat_generator():
            # Emit tokens
            tokens = ["好的", "，已", "按要求", "为您", "调整。"]
            for token in tokens:
                yield f"data: {token}\n\n"
                await asyncio.sleep(0.01)
                
            # Emit final state
            final_data = {
                "reply": reply,
                "updated_plans": updated_plans,
                "message_id": msg_id_assistant
            }
            yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
            
        return StreamingResponse(
            chat_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    return {
        "code": 0,
        "data": {
            "reply": reply,
            "updated_plans": updated_plans,
            "message_id": msg_id_assistant
        }
    }

@app.post("/api/v1/fragrance/{session_id}/regenerate")
async def regenerate_fragrance(session_id: str, payload: dict):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    selected_tags = payload.get("selected_tags")
    plan_count = payload.get("plan_count", 3)
    
    # Clear history
    chat_histories[session_id] = []
    
    # Generate new recommendations
    rec_mock = load_mock_json("fragrance_recommendation.json")
    iceberg_mock = load_mock_json("iceberg_analysis.json")
    
    recommendations = []
    for i in range(plan_count):
        base_plan = rec_mock[i % len(rec_mock)]
        plan = base_plan.copy()
        plan["plan_id"] = f"plan_{i+1}"
        recommendations.append(plan)
        
    sessions[session_id]["recommendations"] = recommendations
    sessions[session_id]["selected_tags"] = selected_tags
    
    # Populate first history message
    chat_histories[session_id].append({
        "id": "msg_initial_regen",
        "role": "assistant",
        "content": f"根据您重新选择的标签，重新生成了 {plan_count} 套香调方案。",
        "updated_plans": None,
        "created_at": "2026-06-13T11:00:00+08:00"
    })
    
    return {
        "code": 0,
        "data": sessions[session_id]
    }

@app.get("/api/v1/fragrance/{session_id}")
async def get_session_details(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "code": 0,
        "data": sessions[session_id]
    }

@app.get("/api/v1/fragrance/{session_id}/history")
async def get_chat_history(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "code": 0,
        "data": {
            "messages": chat_histories[session_id]
        }
    }


# --- F7: System Config ---

@app.get("/api/v1/config/analysis-levels")
async def get_presets():
    return {
        "code": 0,
        "data": {
            "presets": [
                {
                    "level": "standard",
                    "post_count": 10,
                    "comment_count": 20
                },
                {
                    "level": "deep",
                    "post_count": 30,
                    "comment_count": 50
                },
                {
                    "level": "light",
                    "post_count": 5,
                    "comment_count": 10
                }
            ]
        }
    }

@app.get("/api/v1/config/analysis-levels/{level}")
async def get_preset_detail(level: str):
    if level not in ["standard", "deep", "light"]:
        raise HTTPException(status_code=404, detail="Preset level not found")
    return {
        "code": 0,
        "data": {
            "level": level,
            "post_count": 10 if level == "standard" else (30 if level == "deep" else 5),
            "comment_count": 20 if level == "standard" else (50 if level == "deep" else 10)
        }
    }

@app.get("/api/v1/config/ai-providers")
async def get_ai_providers():
    return {
        "code": 0,
        "data": {
            "providers": [
                {"name": "glm", "status": "active", "slots": ["analysis_task", "fragrance_reasoning", "fragrance_chat"]},
                {"name": "openai", "status": "active", "slots": []},
                {"name": "deepseek", "status": "active", "slots": []}
            ]
        }
    }

@app.put("/api/v1/config/ai-providers/{provider_name}")
async def update_ai_provider(provider_name: str, payload: dict, authorization: str = Header(None)):
    # test_f7_unauthorized_config_access expects 401 or 403 if auth missing
    # Let's enforce that auth header exists
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized config access")
        
    if provider_name not in ["openai", "deepseek", "glm"]:
        raise HTTPException(status_code=404, detail="Provider not registered")
        
    # Validate payload types (invalid types -> 422)
    slot = payload.get("slot")
    model = payload.get("model")
    api_key = payload.get("api_key")
    endpoint = payload.get("endpoint")
    
    if slot is not None and not isinstance(slot, str):
        raise HTTPException(status_code=422, detail="Slot must be a string")
    if model is not None and not isinstance(model, str):
        raise HTTPException(status_code=422, detail="Model must be a string")
    if api_key is not None and not isinstance(api_key, str):
        raise HTTPException(status_code=422, detail="API Key must be a string")
    if endpoint is not None and not isinstance(endpoint, str):
        raise HTTPException(status_code=422, detail="Endpoint must be a string")
        
    # Lock for concurrency safety
    async with lock:
        if slot:
            if slot not in ai_routing:
                raise HTTPException(status_code=422, detail="Invalid slot name")
            ai_routing[slot]["provider"] = provider_name
            if model:
                ai_routing[slot]["model"] = model
        # Update provider details
        for slot_key, config in ai_routing.items():
            if config["provider"] == provider_name:
                if api_key:
                    config["api_key"] = api_key
                if endpoint:
                    config["endpoint"] = endpoint
                    
    return {"code": 0, "message": "AI Provider config updated successfully"}

@app.get("/api/v1/config/status")
@app.get("/api/health")
@app.get("/api/v1/health")
async def get_sys_health():
    return {
        "status": "healthy",
        "code": 0,
        "data": {
            "database": "connected",
            "storage": "available",
            "task_queue_size": 0
        }
    }


# --- Pytest Fixtures ---

@pytest.fixture
def client():
    # Use AsyncClient with app context
    return httpx.AsyncClient(app=app, base_url="http://testserver")

@pytest.fixture(autouse=True)
def clean_state():
    reset_db_state()
    yield

# SSE Stream Helper Function exposed as fixture and helper
async def read_sse_stream_func(client: httpx.AsyncClient, url: str, method: str = "GET", json_payload: dict = None, headers: dict = None):
    events = []
    req_headers = {"Accept": "text/event-stream"}
    if headers:
        req_headers.update(headers)
        
    async with client.stream(method, url, json=json_payload, headers=req_headers) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        current_event = {}
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                if current_event:
                    events.append(current_event)
                    current_event = {}
                continue
            if line.startswith("event:"):
                current_event["type"] = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                try:
                    current_event["data"] = json.loads(data_str)
                except json.JSONDecodeError:
                    current_event["data"] = data_str
                    
        if current_event:
            events.append(current_event)
            
    return events

@pytest.fixture
def read_sse_stream():
    return read_sse_stream_func
