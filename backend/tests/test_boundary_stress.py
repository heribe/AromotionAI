import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from PIL import Image
from app.analyzers.media_processor import MediaProcessor
from app.platforms.douyin.collector import DouyinCollector

# ==========================================
# 1. MediaProcessor 边界与压力测试
# ==========================================

def test_preprocess_image_decompression_bomb(tmp_path):
    """
    测试当图片尺寸大于 PIL 的 DecompressionBomb 阈值 (默认约 89M 像素) 时的表现。
    生成的 10000x10000 图片像素数为 1亿，触发 DecompressionBombError。
    系统应该在 except 块中捕获它并抛出相应的 RuntimeError。
    """
    mp = MediaProcessor(test_mode="prod")
    img_path = str(tmp_path / "bomb.jpg")
    
    # 临时调低 MAX_IMAGE_PIXELS 以便在测试中轻松触发 bomb 错误而不需要耗费大量内存
    # 比如设置为 10000 像素
    import PIL.Image
    original_max = PIL.Image.MAX_IMAGE_PIXELS
    PIL.Image.MAX_IMAGE_PIXELS = 10000
    
    try:
        # 创建一个 300x100 = 30000 像素的图片，需 > 2 × MAX_IMAGE_PIXELS (20000)
        # 才能触发 PIL 的 DecompressionBombError（仅 >= 2× 才报错，否则只 Warning）
        img = Image.new("RGB", (300, 100), color="blue")
        img.save(img_path)
        img.close()

        with pytest.raises(RuntimeError) as exc_info:
            mp.preprocess_image(img_path)
        assert "Unsupported or corrupted image format" in str(exc_info.value)
    finally:
        # 恢复原始设置以防止影响其它测试
        PIL.Image.MAX_IMAGE_PIXELS = original_max


def test_preprocess_image_extremely_large_normal(tmp_path):
    """
    测试极端但合法的超长或超宽尺寸缩放
    """
    mp = MediaProcessor(test_mode="prod")
    
    # 横向极端尺寸 10000x10 (未超限 MAX_IMAGE_PIXELS)
    img_path = str(tmp_path / "extreme_horizontal.jpg")
    img = Image.new("RGB", (10000, 10), color="green")
    img.save(img_path)
    img.close()
    
    out_path = str(tmp_path / "extreme_horizontal_out.jpg")
    res_path = mp.preprocess_image(img_path, out_path)
    assert os.path.exists(res_path)
    with Image.open(res_path) as out_img:
        # 10000x10 等比例缩放，最大边 2048
        # scale = 2048 / 10000 = 0.2048
        # new_width = 2048, new_height = max(1, int(10 * 0.2048)) = 2
        assert out_img.size == (2048, 2)


def test_extract_video_frames_duration_boundary(tmp_path):
    """
    测试视频抽帧的时长边界条件：
    1. 极短时长 (如 0.005s)
    2. 极长时长 (如 100000.0s)
    """
    mp = MediaProcessor(test_mode="prod")
    video_path = str(tmp_path / "boundary_video.mp4")
    with open(video_path, "w") as f:
        f.write("fake video data")
        
    out_dir = str(tmp_path / "frames_boundary")
    mock_run_result = MagicMock()
    
    def mock_ffmpeg_run(cmd, *args, **kwargs):
        if cmd[0] == "ffmpeg":
            out_file = cmd[10]
            img = Image.new("RGB", (100, 100), color="red")
            img.save(out_file)
            img.close()
        return MagicMock()

    # 1. 极短时长 0.005 秒。
    # timestamps 为 [0.0, 0.0025, 0.005]
    # 对 ts = 0.005，ts = max(0.0, min(0.005, -0.005)) = 0.0
    mock_run_result.stdout = "0.005\n"
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=lambda cmd, *args, **kwargs: mock_run_result if cmd[0] == "ffprobe" else mock_ffmpeg_run(cmd, *args, **kwargs)):
            paths = mp.extract_video_frames(video_path, out_dir, frame_count=3)
            assert len(paths) == 3

    # 2. 极长时长 100000.0 秒
    mock_run_result.stdout = "100000.0\n"
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=lambda cmd, *args, **kwargs: mock_run_result if cmd[0] == "ffprobe" else mock_ffmpeg_run(cmd, *args, **kwargs)):
            paths = mp.extract_video_frames(video_path, out_dir, frame_count=3)
            assert len(paths) == 3


def test_extract_video_frames_invalid_ffprobe_output(tmp_path):
    """
    测试 ffprobe 输出非数字/损坏格式时的情况
    """
    mp = MediaProcessor(test_mode="prod")
    video_path = str(tmp_path / "invalid_duration.mp4")
    with open(video_path, "w") as f:
        f.write("fake")
        
    out_dir = str(tmp_path / "frames_invalid")
    
    mock_run_result = MagicMock()
    mock_run_result.stdout = "N/A\n"  # 无法转换为 float
    
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", return_value=mock_run_result):
            with pytest.raises(RuntimeError):
                mp.extract_video_frames(video_path, out_dir, frame_count=3)


def test_create_grid_image_count_boundaries(tmp_path):
    """
    测试不同输入图片数量边界的 grid 拼接
    """
    mp = MediaProcessor()
    
    # 准备测试单图
    test_img = str(tmp_path / "src.jpg")
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(test_img)
    img.close()
    
    # 1. 刚好有 10 张图片 (匹配默认 grid)
    out_grid_10 = str(tmp_path / "grid_10.jpg")
    res_10 = mp.create_grid_image([test_img] * 10, out_grid_10)
    assert os.path.exists(res_10)
    
    # 2. 只有 1 张图片 (远少于 10 张)
    out_grid_1 = str(tmp_path / "grid_1.jpg")
    res_1 = mp.create_grid_image([test_img], out_grid_1)
    assert os.path.exists(res_1)
    
    # 3. 传入 100 张图片 (远大于 10 张)
    out_grid_100 = str(tmp_path / "grid_100.jpg")
    res_100 = mp.create_grid_image([test_img] * 100, out_grid_100)
    assert os.path.exists(res_100)


def test_create_grid_image_invalid_cell_size(tmp_path):
    """
    测试传入异常 cell_size 的情况
    """
    mp = MediaProcessor()
    out_grid = str(tmp_path / "grid_cell_size.jpg")
    
    # 传入 cell_size = 0，预期触发 ValueError
    with pytest.raises(ValueError):
        mp.create_grid_image([], out_grid, cell_size=0)
        
    # 传入 cell_size = -10，预期触发 ValueError
    with pytest.raises(ValueError):
        mp.create_grid_image([], out_grid, cell_size=-10)


# ==========================================
# 2. DouyinCollector 边界与压力测试
# ==========================================

@pytest.mark.asyncio
async def test_douyin_collector_flatten_cookies_malformed():
    """
    测试 _flatten_cookies 在收到异常数据结构时的表现
    """
    collector = DouyinCollector()
    
    # 1. 传入空列表或 None
    assert collector._flatten_cookies([]) == {}
    assert collector._flatten_cookies(None) == {}
    
    # 2. 元素中缺失 value
    cookies_missing_val = [{"name": "cookie1"}]
    assert collector._flatten_cookies(cookies_missing_val) == {}
    
    # 3. 元素中缺失 name
    cookies_missing_name = [{"value": "val1"}]
    assert collector._flatten_cookies(cookies_missing_name) == {}

    # 4. 传入非 Dict 类型的元素 (如 None) - 应该优雅处理过滤跳过
    cookies_with_none = [None, {"name": "c", "value": "v"}]
    assert collector._flatten_cookies(cookies_with_none) == {"c": "v"}


@pytest.mark.asyncio
async def test_douyin_collector_select_posts_robustness():
    """
    测试 select_posts 在 config 参数异常时的表现
    """
    collector = DouyinCollector()
    posts = [{"id": "1", "statistics": {"digg_count": 10}}]
    
    # 1. config = None (预期在防御后不会抛 AttributeError，而是成功返回结果)
    selected = collector.select_posts(posts, None)
        
    # 2. config 缺省 top_n 和 recent_n (使用默认值 5)
    selected = collector.select_posts(posts, {})
    assert len(selected) == 1
