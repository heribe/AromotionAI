# Part1 后端开发文档 — 用户画像分析

> **文档版本**: v1.0  
> **创建时间**: 2026-06-13  
> **依赖文档**: `00-global-dev-guide.md`

---

## 一、模块概述

Part1 负责从社交媒体平台采集博主及其粉丝数据，通过 AI 分析生成四维度用户画像标签。

### 1.1 处理流程

```
输入: 博主链接 + 分析等级配置
    ↓
Step 1: 博主基础数据采集
    → Profile API → 基本资料
    → Post API → 帖子列表 → 选取分析目标帖
    ↓
Step 2: 媒体下载 & 预处理
    → 下载封面图 → 图片预处理管道
    → 下载视频 → ffmpeg 提取关键帧 → 预处理
    ↓
Step 3: 评论采集
    → Playwright → 评论列表
    → 评论者 sec_uid 去重
    → 评论者 Profile API → 评论者资料
    → 评论者 Post API → 评论者帖子 & 封面图
    ↓
Step 4: 内容分析
    → 视觉分析器: 封面图/帧/组图 → AI 分析穿搭/消费/场景
    → 评论分析器: 评论文本 → 关键词/情感/消费意图
    ↓
Step 5: 标签生成
    → 标签聚合器: 合并所有分析结果 → 四维度标签 + 比例
    → 生成文字报告
    ↓
输出: ProfileReport (四维度标签 + 比例 + 文字报告)
```

---

## 二、API 详细设计

### 2.1 创建分析任务

**`POST /api/v1/analysis/create`**

请求体:
```json
{
  "blogger_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "platform": "douyin",
  "analysis_level": "standard",
  "custom_config": null
}
```

响应:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "a1b2c3d4-...",
    "status": "pending",
    "created_at": "2026-06-13T10:00:00+08:00"
  }
}
```

**自定义配置请求示例** (`analysis_level: "custom"`):
```json
{
  "blogger_url": "https://www.douyin.com/user/...",
  "platform": "douyin",
  "analysis_level": "custom",
  "custom_config": {
    "post_selection": {
      "top_count": 4,
      "recent_count": 4,
      "sort_by": "likes"
    },
    "comment": {
      "per_post_count": 30,
      "sort_by": "hot"
    },
    "commenter_analysis": {
      "enabled": true,
      "max_count": 50,
      "analyze_posts": true,
      "posts_per_commenter": 3,
      "analyze_post_content": true,
      "analyze_video": false
    },
    "sub_comment": {
      "enabled": true,
      "count": 5
    },
    "visual_analysis": {
      "cover_analysis": true,
      "video_frame_analysis": true,
      "frames_per_video": 5,
      "analyze_frames_count": 3,
      "fan_cover_mode": "grid",
      "grid_size": 10
    }
  }
}
```

**业务逻辑**:
1. 验证 `blogger_url` 格式，提取平台类型
2. 验证对应平台的 Cookie 是否存在且有效
3. 如果 `analysis_level` 是预设值，加载预设配置；如果是 `custom`，使用 `custom_config`
4. 创建 `AnalysisTask` 记录
5. 启动异步任务
6. 返回 `task_id`

---

### 2.2 获取分析任务详情

**`GET /api/v1/analysis/{task_id}`**

响应:
```json
{
  "code": 0,
  "data": {
    "task_id": "a1b2c3d4-...",
    "platform": "douyin",
    "blogger_url": "https://www.douyin.com/user/...",
    "analysis_level": "standard",
    "status": "analyzing",
    "progress": 60,
    "current_step": "正在分析视频帧",
    "blogger_info": {
      "nickname": "xxx",
      "avatar_url": "...",
      "follower_count": 12345
    },
    "created_at": "2026-06-13T10:00:00+08:00",
    "updated_at": "2026-06-13T10:05:00+08:00",
    "completed_at": null
  }
}
```

---

### 2.3 SSE 进度推送

**`GET /api/v1/analysis/{task_id}/progress`**

返回 `text/event-stream` 类型。

事件流示例:
```
event: progress
data: {"task_id":"a1b2c3d4","status":"collecting","progress":10,"current_step":"正在采集博主资料","sub_steps":[{"name":"博主资料","status":"running"},{"name":"帖子列表","status":"pending"},{"name":"媒体下载","status":"pending"},{"name":"评论采集","status":"pending"},{"name":"评论者分析","status":"pending"},{"name":"内容分析","status":"pending"},{"name":"标签生成","status":"pending"}]}

event: step_complete
data: {"step":"博主资料","summary":"采集成功: xxx, 粉丝数 12345"}

event: progress
data: {"task_id":"a1b2c3d4","status":"collecting","progress":20,"current_step":"正在采集帖子列表","sub_steps":[{"name":"博主资料","status":"completed"},{"name":"帖子列表","status":"running"},{"name":"媒体下载","status":"pending"},{"name":"评论采集","status":"pending"},{"name":"评论者分析","status":"pending"},{"name":"内容分析","status":"pending"},{"name":"标签生成","status":"pending"}]}

event: complete
data: {"task_id":"a1b2c3d4","report_id":"xxx"}
```

**实现要点**:
```python
# app/api/v1/analysis.py
from fastapi.responses import StreamingResponse

@router.get("/{task_id}/progress")
async def stream_progress(task_id: str):
    async def event_generator():
        task_manager = get_task_manager()
        async for event in task_manager.subscribe(task_id):
            yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲
        }
    )
```

---

### 2.4 获取画像报告

**`GET /api/v1/analysis/{task_id}/report`**

响应:
```json
{
  "code": 0,
  "data": {
    "task_id": "a1b2c3d4-...",
    "blogger_info": {
      "nickname": "xxx",
      "avatar_url": "...",
      "follower_count": 12345,
      "platform": "douyin"
    },
    "report": {
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
    },
    "full_report_markdown": "## 博主 xxx 粉丝画像\n\n### 一、气候-消费带\n..."
  }
}
```

---

### 2.5 获取标签数据

**`GET /api/v1/analysis/{task_id}/tags`**

此接口返回与报告相同的标签数据，但格式更适合前端标签筛选页使用。

响应:
```json
{
  "code": 0,
  "data": {
    "dimensions": [
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
            "is_mutually_exclusive": true,
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
            "is_mutually_exclusive": false,
            "max_select": null
          }
        ]
      }
      // ... 其他维度
    ]
  }
}
```

**关键设计**:
- 每个 tag 标注 `is_default_selected`（系统自动选中比例最高的）
- 标注 `is_mutually_exclusive` 和 `mutually_exclusive_group`（互斥标签组）
- `max_select` 控制最多可选几个（null = 不限）

---

### 2.6 获取分析任务列表

**`GET /api/v1/analysis/list?page=1&page_size=20&status=all`**

查询参数:
| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | int | 页码，默认 1 |
| `page_size` | int | 每页数量，默认 20 |
| `status` | string | 筛选状态: all/pending/collecting/analyzing/completed/failed |

响应:
```json
{
  "code": 0,
  "data": {
    "total": 15,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "task_id": "a1b2c3d4-...",
        "platform": "douyin",
        "blogger_info": {
          "nickname": "xxx",
          "avatar_url": "..."
        },
        "analysis_level": "standard",
        "status": "completed",
        "progress": 100,
        "created_at": "2026-06-13T10:00:00+08:00",
        "completed_at": "2026-06-13T10:12:00+08:00",
        "has_fragrance_session": true
      }
    ]
  }
}
```

---

### 2.7 删除分析任务

**`DELETE /api/v1/analysis/{task_id}`**

- 删除数据库记录
- 删除关联的媒体文件（`backend/data/media/{task_id}/`）
- 删除关联的 FragranceSession 和 ChatMessage

---

## 三、数据采集 — 抖音平台

### 3.1 DouyinCollector 实现

参考现有实验 `others/tx_agent/README.md`，核心技术方案不变：

#### 3.1.1 Cookie 管理

```python
class DouyinCollector(PlatformCollector):
    def __init__(self, cookie_service: CookieService):
        self.cookie_service = cookie_service
    
    async def _get_cookie_header(self) -> str:
        """获取 Cookie 字符串用于请求"""
        cookie = await self.cookie_service.get_valid_cookie("douyin")
        if not cookie:
            raise CookieExpiredError("抖音 Cookie 已过期，请重新上传")
        return "; ".join(f"{c['name']}={c['value']}" for c in cookie.cookie_data)
```

#### 3.1.2 双通道策略

| 通道 | 工具 | 适用场景 |
|---|---|---|
| curl 直连 | curl_cffi + Cookie | Profile API、Post API |
| Playwright | headless Chromium + Stealth + Cookie | Comment API、评论者资料 |

#### 3.1.3 API 端点

| 端点 | 用途 | 通道 |
|---|---|---|
| `/aweme/v1/web/user/profile/other/` | 用户资料 | curl |
| `/aweme/v1/web/aweme/post/` | 帖子列表 | curl |
| `/aweme/v1/web/comment/list/` | 评论列表 | Playwright |
| `/aweme/v1/web/comment/list/reply/` | 子评论 | Playwright |

#### 3.1.4 视频下载双通道

- **通道A**: Post API 新鲜 URL + Cookie（近期帖子）
- **通道B**: 移动端分享页 iesdouyin.com（所有帖子）
- **策略**: 先 A 后 B，文件 < 10KB 视为失败

#### 3.1.5 帖子选择算法

```python
async def select_posts(self, posts: list[dict], config: dict) -> list[dict]:
    """选择需要分析的帖子"""
    top_count = config["post_selection"]["top_count"]
    recent_count = config["post_selection"]["recent_count"]
    sort_by = config["post_selection"]["sort_by"]
    
    # 按热度排序取 Top N
    sort_key = {
        "likes": lambda p: p.get("statistics", {}).get("digg_count", 0),
        "comments": lambda p: p.get("statistics", {}).get("comment_count", 0),
        "shares": lambda p: p.get("statistics", {}).get("share_count", 0),
    }[sort_by]
    
    sorted_by_hot = sorted(posts, key=sort_key, reverse=True)
    top_posts = sorted_by_hot[:top_count]
    
    # 按时间排序取最近 N（与 Top 去重）
    top_ids = {p["aweme_id"] for p in top_posts}
    sorted_by_time = sorted(posts, key=lambda p: p.get("create_time", 0), reverse=True)
    recent_posts = []
    for p in sorted_by_time:
        if p["aweme_id"] not in top_ids:
            recent_posts.append(p)
        if len(recent_posts) >= recent_count:
            break
    
    return top_posts + recent_posts
```

---

### 3.2 Playwright 配置

```python
# platforms/douyin/collector.py

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
window.chrome = { runtime: {} };
"""

async def _create_browser_context(self):
    """创建带隐身配置的浏览器上下文"""
    browser = await self.playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled'
        ]
    )
    
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
        viewport={'width': 1920, 'height': 1080}
    )
    
    # Cookie 格式转换
    pw_cookies = self._convert_cookies_for_playwright(raw_cookies)
    await context.add_cookies(pw_cookies)
    
    page = await context.new_page()
    await page.add_init_script(STEALTH_JS)
    
    return browser, context, page
```

**⚠️ 关键注意事项**（来自实验总结）:
1. 不要导航到 douyin.com 首页（会超时），直接导航到 `/video/{id}` 页面
2. sameSite 只接受 `Strict`/`Lax`/`None`，其他值需过滤
3. 评论者封面 URL 有时效，需要 Playwright 重新 fetch 获取新鲜 URL
4. Post API 不支持 cursor 分页，用 `count=70` 一次取完

---

## 四、媒体处理

### 4.1 图片预处理管道

```python
# analyzers/media_processor.py

class MediaProcessor:
    """图片/视频预处理"""
    
    async def preprocess_image(self, input_path: str, output_path: str = None) -> str:
        """
        自动检测并处理图片问题:
        - HEIF/HEIC → JPEG
        - WebP → JPEG
        - AVIF → JPEG
        - 超大图(>2048px) → 缩放到 2048 以内
        """
        ...
    
    async def extract_video_frames(
        self, 
        video_path: str, 
        output_dir: str, 
        frame_count: int = 5
    ) -> list[str]:
        """
        从视频中提取关键帧
        使用 ffmpeg 的 select 过滤器提取均匀分布的帧
        返回帧文件路径列表
        """
        ...
    
    async def create_grid_image(
        self, 
        image_paths: list[str], 
        output_path: str,
        grid_size: int = 10,
        cell_size: int = 320
    ) -> str:
        """
        将多张图片拼接成网格组图
        默认 2×5 布局，每格 320×320
        """
        ...
```

### 4.2 视频帧提取策略

```python
# 提取 N 帧均匀分布的关键帧
ffmpeg_cmd = [
    'ffmpeg', '-y', '-i', video_path,
    '-vf', f'select=not(mod(n\\,{total_frames // frame_count}))',
    '-vsync', 'vfn',
    '-frames:v', str(frame_count),
    '-q:v', '3',
    f'{output_dir}/frame_%02d.jpg'
]
```

### 4.3 组图生成策略

> [!WARNING]
> 组图分析（grid mode）在 320×320 缩略图下会丢失细节，仅适合快速分类。如果需要精细分析（如品牌识别、面料判断），应使用 `individual` 模式。

---

## 五、内容分析器

### 5.1 视觉分析器 (VisualAnalyzer)

```python
class VisualAnalyzer(BaseAnalyzer):
    """封面图/视频帧/组图的视觉分析"""
    
    async def analyze_cover(self, image_path: str) -> dict:
        """
        详细分析单张封面图
        Prompt: 你是时尚与消费分析师。分析这张图：
        1) 穿搭单品（品类/颜色/材质/品牌线索）
        2) 搜索关键词
        3) 场景和城市线索
        4) 消费水平（低/中/中高/高）
        5) 生活方式/审美倾向
        返回 JSON 格式。
        """
        ...
    
    async def analyze_video_frame(self, frame_path: str) -> dict:
        """
        分析视频帧（简洁版）
        Prompt: 简洁分析：穿搭单品、搭配变化、消费水平。JSON格式。
        """
        ...
    
    async def analyze_grid(self, grid_path: str, person_count: int) -> list[dict]:
        """
        批量分析组图（2×5 网格，每格一个用户）
        Prompt: 这张图是2×5网格，每格是不同用户的封面。
        请逐格（左到右上到下）分析：穿搭/人物/主题、消费水平、审美风格。
        返回 JSON 数组。
        """
        ...
```

### 5.2 评论语义分析器 (CommentAnalyzer)

```python
class CommentAnalyzer(BaseAnalyzer):
    """评论文本的语义分析"""
    
    async def analyze_comments(self, comments: list[dict]) -> dict:
        """
        分析一批评论文本
        输出:
        - keyword_stats: 关键词频次统计
        - sentiment_distribution: 情感分类分布
        - purchase_intent: 购买意图信号
        - dialect_features: 方言/梗特征
        - interaction_type: 互动类型分布
        """
        ...
```

### 5.3 标签聚合器 (ProfileAggregator)

```python
class ProfileAggregator(BaseAnalyzer):
    """汇总所有分析结果，生成四维度标签报告"""
    
    async def aggregate(
        self,
        blogger_profile: dict,
        visual_analysis: list[dict],
        comment_analysis: dict,
        commenter_profiles: list[dict],
        fan_visual_analysis: list[dict]
    ) -> ProfileReport:
        """
        输入所有原始分析结果，输出四维度标签报告
        
        处理逻辑:
        1. 地域数据聚合: province + city + store_region → 气候带/城市线级/文化圈
        2. 消费推断: 穿搭分析 → 价格带 + 评论分析 → 消费动机
        3. 穿搭映射: 视觉分析结果 → 穿搭风格/场景/色彩/完整度
        4. 生活方式: 评论者帖子分类 → 兴趣/社交/审美/时段
        5. 调用 AI 生成综合判断和文字报告
        """
        ...
```

---

## 六、分析流程编排

### 6.1 AnalysisService

```python
class AnalysisService:
    """分析任务编排服务"""
    
    def __init__(
        self,
        collector: PlatformCollector,
        media_processor: MediaProcessor,
        visual_analyzer: VisualAnalyzer,
        comment_analyzer: CommentAnalyzer,
        profile_aggregator: ProfileAggregator,
        storage: StorageProvider,
        task_manager: TaskManager
    ):
        ...
    
    async def run_analysis(self, task: AnalysisTask) -> ProfileReport:
        """执行完整分析流程"""
        
        try:
            # Step 1: 博主基础数据
            await self._emit_progress(task, "collecting", 5, "正在采集博主资料")
            blogger = await self.collector.get_blogger_profile(task.blogger_url)
            posts = await self.collector.get_blogger_posts(blogger.uid, count=70)
            selected_posts = await self.collector.select_posts(posts, task.config)
            
            # Step 2: 媒体下载 & 预处理
            await self._emit_progress(task, "collecting", 15, "正在下载封面图和视频")
            covers = await self._download_covers(selected_posts, task.id)
            if task.config["visual_analysis"]["video_frame_analysis"]:
                videos = await self._download_videos(selected_posts, task.id)
                frames = await self._extract_frames(videos, task.id)
            
            # Step 3: 评论采集
            await self._emit_progress(task, "collecting", 30, "正在采集评论")
            comments = await self._collect_comments(selected_posts, task.config)
            commenters = await self._collect_commenter_profiles(comments, task.config)
            fan_covers = await self._download_fan_covers(commenters, task)
            
            # Step 4: 内容分析
            await self._emit_progress(task, "analyzing", 50, "正在分析博主内容")
            visual_results = await self._analyze_visuals(covers, frames, fan_covers, task.config)
            comment_results = await self.comment_analyzer.analyze_comments(comments)
            
            # Step 5: 标签生成
            await self._emit_progress(task, "analyzing", 80, "正在生成画像标签")
            report = await self.profile_aggregator.aggregate(
                blogger, visual_results, comment_results, commenters, fan_covers
            )
            
            # 保存结果
            await self._save_report(task, report)
            await self._emit_progress(task, "completed", 100, "分析完成")
            
            return report
            
        except CookieExpiredError as e:
            await self._emit_error(task, str(e))
            raise
        except Exception as e:
            await self._emit_error(task, f"分析过程中出错: {str(e)}")
            raise
```

### 6.2 进度计算

各步骤的预估进度比例（可按实际耗时调整）:

| 步骤 | 进度范围 | 预估耗时占比 |
|---|---|---|
| 博主基础数据 | 0-10% | 5% |
| 媒体下载 & 预处理 | 10-30% | 20% |
| 评论采集 & 评论者分析 | 30-55% | 30% |
| 内容分析（视觉+语义） | 55-85% | 30% |
| 标签生成 & 报告 | 85-100% | 15% |

---

## 七、异步任务管理

### 7.1 TaskManager

```python
class TaskManager:
    """异步任务管理器 + SSE 事件推送"""
    
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
    
    async def submit(self, task_id: str, coro) -> None:
        """提交异步任务"""
        task = asyncio.create_task(coro)
        self._tasks[task_id] = task
    
    async def emit(self, task_id: str, event_type: str, data: dict) -> None:
        """向所有订阅者推送事件"""
        if task_id in self._subscribers:
            event = {"type": event_type, "data": data}
            for queue in self._subscribers[task_id]:
                await queue.put(event)
    
    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """订阅任务事件流"""
        queue = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event["type"] in ("complete", "error"):
                    break
        finally:
            self._subscribers[task_id].remove(queue)
    
    def get_status(self, task_id: str) -> str:
        """获取任务状态"""
        ...
    
    async def cancel(self, task_id: str) -> None:
        """取消任务"""
        ...
```

> [!NOTE]
> 第一版使用内存中的 asyncio.Queue 实现。后续扩展到多实例部署时，需要切换为 Redis Pub/Sub + Celery 的方案。Queue 断连后重连可以从数据库中恢复已完成步骤的状态。

---

## 八、Cookie 管理

### 8.1 API

**`POST /api/v1/cookies/upload`**

请求: `multipart/form-data`
| 字段 | 类型 | 说明 |
|---|---|---|
| `platform` | string | "douyin" / "xiaohongshu" / "taobao" |
| `file` | File | Cookie JSON 文件 |

**`GET /api/v1/cookies/status`**

响应:
```json
{
  "code": 0,
  "data": {
    "cookies": [
      {
        "platform": "douyin",
        "is_valid": true,
        "uploaded_at": "2026-06-12T10:00:00+08:00",
        "last_checked_at": "2026-06-13T09:00:00+08:00"
      },
      {
        "platform": "taobao",
        "is_valid": false,
        "uploaded_at": "2026-06-10T10:00:00+08:00",
        "last_checked_at": "2026-06-13T09:00:00+08:00"
      }
    ]
  }
}
```

### 8.2 Cookie 有效性检测

```python
class CookieService:
    async def validate_cookie(self, platform: str) -> bool:
        """
        验证 Cookie 是否有效
        - 抖音: 尝试调用 Profile API，检查返回状态
        - 淘宝: 尝试搜索请求，检查是否被拦截
        """
        ...
    
    async def get_valid_cookie(self, platform: str) -> PlatformCookie | None:
        """获取有效的 Cookie，无效返回 None"""
        cookie = await self.repo.get_by_platform(platform)
        if not cookie:
            # 检查后端配置文件
            cookie = await self._load_from_config(platform)
        if cookie and not cookie.is_valid:
            # 重新验证
            is_valid = await self.validate_cookie(platform)
            if not is_valid:
                return None
        return cookie
```

---

## 九、四维度标签体系

> [!IMPORTANT]
> 标签体系直接复用现有实验中定义的体系，详见 `others/tx_agent/README.md` 第四章。此处仅列出维度结构，具体标签定义请参考该文档。

### 9.1 维度结构

| 维度 ID | 维度名称 | 子维度 |
|---|---|---|
| `climate_consumption` | 气候-消费带 | 气候带、城市线级、文化圈暗示、地域集中度 |
| `fragrance_consumption` | 香氛消费推断 | 价格带匹配、消费动机、决策路径、消费频次 |
| `fashion_fragrance_map` | 穿搭风格-香调映射 | 穿搭风格、穿搭场景、色彩偏好、穿搭完整度 |
| `lifestyle_scenario` | 生活方式-用香场景 | 核心兴趣、社交活跃度、审美性格、用香时段、内容消费特征 |

### 9.2 互斥标签规则

| 子维度 | 互斥规则 | 说明 |
|---|---|---|
| 气候带 | 互斥（最多选1） | 不同气候偏好差异大 |
| 城市线级 | 非互斥（可多选） | 粉丝可能分布在多个线级 |
| 地域集中度 | 互斥（最多选1） | 只有一种集中度模式 |
| 价格带匹配 | 非互斥（可多选） | 可能覆盖多个价格段 |
| 穿搭风格 | 非互斥（可多选） | 粉丝风格多样 |
| 审美性格 | 非互斥（可多选） | 可以兼有 |

> [!NOTE]
> 互斥规则在标签筛选页会影响 UI 交互：互斥标签用单选按钮（Radio），非互斥用复选框（Checkbox）。

---

## 十、错误处理

### 10.1 采集阶段错误

| 错误场景 | 处理策略 |
|---|---|
| Cookie 过期 | 立即终止任务，提示用户重新上传 |
| API 请求被封（bd-ticket-guard） | 自动切换到 Playwright 通道 |
| 视频下载失败 | 自动切换通道B，仍失败则跳过该视频 |
| 图片下载失败 | 记录日志，继续下一张 |
| 评论者资料获取失败 | 记录日志，继续下一个 |

### 10.2 分析阶段错误

| 错误场景 | 处理策略 |
|---|---|
| AI API 调用失败（限流） | 自动重试（最多3次，指数退避） |
| AI API 返回格式异常 | 重试一次，仍异常则记录原始返回 |
| 图片无法识别 | 跳过该图片，使用其他数据补充 |

---

## 十一、待进一步讨论的问题

> [!WARNING]
> 以下问题需要在开发过程中逐步细化。

1. **子评论 API** (`/aweme/v1/web/comment/list/reply/`) 的可行性 — 需要实际测试是否可以通过 Playwright 调用
2. **组图精度问题** — 是否需要在不同分析等级下自动切换 grid/individual 模式，还是完全由配置决定
3. **分析过程中的数据持久化** — 如果任务中断（服务重启），是否需要从断点恢复？第一版建议不做，标记为 failed 让用户重新发起
4. **store_region 映射表** — 是否需要扩展更多地区编码？
5. **淘宝价格搜索** — 是否纳入第一版？目前实验中有但不确定产品中是否需要
6. **并发控制** — AI API 并发限制（GLM 限制3个并发）如何在多任务场景下管理？
