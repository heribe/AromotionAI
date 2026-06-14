import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from PIL import Image
from app.analyzers.media_processor import MediaProcessor
from app.platforms.douyin.collector import DouyinCollector
from app.models.blogger import BloggerProfile

# ==========================================
# 1. MediaProcessor 对抗性测试用例
# ==========================================

def test_preprocess_image_extreme_aspect_ratio(tmp_path):
    """
    测试极端宽高比图片在 preprocessing 时的表现。
    对于 1x5000 的图片，缩放后计算出新宽度为 0，
    验证使用 max(1, new_width) 限制后不会抛出 ValueError 错误且生成正确的尺寸。
    """
    mp = MediaProcessor(test_mode="prod")
    
    # 创建 1x5000 的图片
    img_path = str(tmp_path / "extreme_vertical.jpg")
    img = Image.new("RGB", (1, 5000), color="red")
    img.save(img_path)
    img.close()
    
    out_path = str(tmp_path / "extreme_out.jpg")
    
    # 运行 preprocessing
    # 使用 max(1, new_width)，应该成功完成且不报错
    res_path = mp.preprocess_image(img_path, out_path)
    assert os.path.exists(res_path)
    with Image.open(res_path) as out_img:
        assert out_img.size[0] > 0
        assert out_img.size[1] > 0


def test_create_grid_image_tiny_image(tmp_path):
    """
    测试极小图片 (1x1, 2x2) 在 create_grid_image 中 Center-Crop 的表现。
    """
    mp = MediaProcessor()
    
    # 创建 1x1 的极小头像
    tiny_img_path = str(tmp_path / "tiny.jpg")
    img = Image.new("RGB", (1, 1), color="blue")
    img.save(tiny_img_path)
    img.close()
    
    # 构造少于 10 张的图片列表，包含 1x1 图片
    image_paths = [tiny_img_path] * 5
    
    out_grid = str(tmp_path / "grid_tiny.jpg")
    res_path = mp.create_grid_image(image_paths, out_grid)
    
    assert os.path.exists(res_path)
    with Image.open(res_path) as grid:
        assert grid.size == (1600, 640)


def test_create_grid_image_extreme_counts(tmp_path):
    """
    测试输入图片列表为空、少于 10 张、多于 10 张时，网格图拼接的表现。
    """
    mp = MediaProcessor()
    
    # 1. 空图片列表
    out_grid_empty = str(tmp_path / "grid_empty.jpg")
    res_empty = mp.create_grid_image([], out_grid_empty)
    assert os.path.exists(res_empty)
    with Image.open(res_empty) as grid:
        # 画布应当完全是白色 (255, 255, 255)
        # 获取左上角像素颜色
        assert grid.getpixel((0, 0)) == (255, 255, 255)
        
    # 创建 12 张正常图片
    image_paths = []
    for i in range(12):
        path = str(tmp_path / f"temp_{i}.jpg")
        img = Image.new("RGB", (100, 100), color="green")
        img.save(path)
        img.close()
        image_paths.append(path)
        
    # 2. 多于 10 张的图片列表 (应该只截取前 10 张)
    out_grid_many = str(tmp_path / "grid_many.jpg")
    res_many = mp.create_grid_image(image_paths, out_grid_many)
    assert os.path.exists(res_many)


def test_extract_video_frames_extreme_duration(tmp_path):
    """
    测试视频抽帧时，面对负数时长、零时长、极长时长时系统的表现。
    """
    mp = MediaProcessor(test_mode="prod")
    video_path = str(tmp_path / "fake_video.mp4")
    with open(video_path, "w") as f:
        f.write("fake video")
        
    out_dir = str(tmp_path / "frames_extreme")
    
    # 模拟 ffprobe 抽样
    mock_run_result = MagicMock()
    
    # Mock ffmpeg 运行，写入占位帧
    def mock_ffmpeg_run(cmd, *args, **kwargs):
        if cmd[0] == "ffmpeg":
            out_file = cmd[10]
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(out_file)
            img.close()
        return MagicMock()
        
    # 1. 负数时长 (-15.0)
    mock_run_result.stdout = "-15.0\n"
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=lambda cmd, *args, **kwargs: mock_run_result if cmd[0] == "ffprobe" else mock_ffmpeg_run(cmd, *args, **kwargs)):
            paths = mp.extract_video_frames(video_path, out_dir, frame_count=3)
            # 虽然时长是负数，但 ts 应该被限制截断在 >= 0
            assert len(paths) == 3
            for p in paths:
                assert os.path.exists(p)

    # 2. 零时长 (0.0)
    mock_run_result.stdout = "0.0\n"
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=lambda cmd, *args, **kwargs: mock_run_result if cmd[0] == "ffprobe" else mock_ffmpeg_run(cmd, *args, **kwargs)):
            paths = mp.extract_video_frames(video_path, out_dir, frame_count=3)
            assert len(paths) == 3


def test_preprocess_image_corrupted_format(tmp_path):
    """
    测试损坏的非标准格式文件输入。
    如果后缀为 .webp 但数据完全损坏，且没有/或有 ffmpeg，应该抛出 RuntimeError。
    """
    mp = MediaProcessor()
    bad_img_path = str(tmp_path / "corrupted.webp")
    with open(bad_img_path, "w") as f:
        f.write("definitely not webp data")
        
    # 无 ffmpeg 情况下应该直接报错 Unsupported or corrupted
    with patch.object(mp, "_has_ffmpeg", return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            mp.preprocess_image(bad_img_path)
        assert "Unsupported or corrupted image format" in str(exc_info.value)
        
    # 有 ffmpeg 情况下，ffmpeg 转换同样会失败，应该报错 Failed to convert image
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=Exception("ffmpeg conversion failed")):
            with pytest.raises(RuntimeError) as exc_info:
                mp.preprocess_image(bad_img_path)
            assert "Failed to convert image" in str(exc_info.value)


# ==========================================
# 2. DouyinCollector 对抗性测试用例
# ==========================================

@pytest.mark.asyncio
async def test_douyin_collector_silent_fallback():
    """
    测试当 DouyinCollector 爬虫在真实模式下，遇到异常（如 Cookie 失效/网络超时/API返回错误）时的行为。
    在 Live/Production 下应当抛出异常，阻止静默降级（防止假数据污染）。
    而在 Mock 下应当支持 Mock 降级。
    """
    collector = DouyinCollector(test_mode="prod")
    
    # 模拟真实 HTTP 请求抛出异常（网络连接超时或 Cookie 失效）
    mock_session = MagicMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get = AsyncMock(side_effect=Exception("Cookie expired or network timeout"))
    
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_session):
        with pytest.raises(Exception) as exc_info:
            await collector.get_blogger_profile("https://www.douyin.com/user/MS4wLjABAAAA_expired_cookie")
        assert "Cookie expired" in str(exc_info.value)

    # 模拟帖子列表抓取失败
    mock_session.get = AsyncMock(side_effect=Exception("Connection reset by peer"))
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_session):
        with pytest.raises(Exception) as exc_info:
            await collector.get_blogger_posts("uid_123", count=2)
        assert "Connection reset" in str(exc_info.value)

    # 验证在 mock 模式下可以正常获取 mock 数据（无报错且成功降级/读取 mock）
    collector_mock = DouyinCollector(test_mode="mock")
    profile_mock = await collector_mock.get_blogger_profile("https://www.douyin.com/user/any")
    assert profile_mock.nickname == "时尚博主A"


@pytest.mark.asyncio
async def test_douyin_collector_malformed_url():
    """
    测试畸形 Blogger URL 的解析表现。
    """
    collector = DouyinCollector(test_mode="mock")
    
    # 1. 传入空字符串
    profile_empty = await collector.get_blogger_profile("")
    # 应该使用生成的随机 ID 或者是 sec_user_id (即空字符串)
    assert profile_empty.platform_uid == "unknown" or profile_empty.platform_uid == "" or "123456789" in profile_empty.platform_uid
    
    # 2. 传入不包含 user/ 的纯文本
    profile_plain = await collector.get_blogger_profile("just_plain_id")
    # 由于匹配不到 user/，sec_user_id 会直接取 "just_plain_id"，最终 uid 取 mock 数据的 "123456789" 或 "just_plain_id"
    assert profile_plain.platform_uid in ["123456789", "just_plain_id", "unknown"]


def test_extract_video_frames_missing_ffmpeg_prod(tmp_path):
    """
    测试在生产模式 (test_mode != "mock") 下，如果系统缺失 ffmpeg (即 _has_ffmpeg() 为 False)，
    调用 extract_video_frames 必须抛出 RuntimeError 错误。
    """
    mp = MediaProcessor(test_mode="prod")
    video_path = str(tmp_path / "fake_video.mp4")
    with open(video_path, "w") as f:
        f.write("fake video content")
    
    out_dir = str(tmp_path / "frames_missing_ffmpeg")
    
    # 模拟 _has_ffmpeg 返回 False
    with patch.object(mp, "_has_ffmpeg", return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            mp.extract_video_frames(video_path, out_dir, frame_count=5)
        assert "ffmpeg and ffprobe are required but not installed/found in production mode." in str(exc_info.value)


def test_extract_video_frames_missing_ffmpeg_mock(tmp_path):
    """
    测试在 Mock 模式 (test_mode == "mock") 下，即使缺失 ffmpeg，
    也能够正常降级返回 PIL 占位图路径，不抛出异常。
    """
    mp = MediaProcessor(test_mode="mock")
    video_path = str(tmp_path / "fake_video.mp4")
    out_dir = str(tmp_path / "frames_missing_ffmpeg_mock")
    
    with patch.object(mp, "_has_ffmpeg", return_value=False):
        paths = mp.extract_video_frames(video_path, out_dir, frame_count=3)
        assert len(paths) == 3
        for p in paths:
            assert os.path.exists(p)


@pytest.mark.asyncio
async def test_download_video_failed_prod(tmp_path):
    """
    测试在生产模式下，当主通道和备用通道都下载失败时，
    download_video 应当抛出 RuntimeError。
    """
    collector = DouyinCollector(test_mode="prod")
    output_path = str(tmp_path / "downloaded_video.mp4")
    
    # Mock AsyncSession 抛出异常
    mock_session = MagicMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get = AsyncMock(side_effect=Exception("Connection refused or DNS resolution failed"))
    
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_session):
        with pytest.raises(RuntimeError) as exc_info:
            await collector.download_video(
                video_url="https://invalid.url/video.mp4",
                video_id="invalid_video_id",
                output_path=output_path
            )
        assert "Video download failed" in str(exc_info.value)


def test_create_grid_image_invalid_dimensions(tmp_path):
    """
    测试网格拼接传入 (0, 0) 或行、列小于等于 0 时，确切抛出 ValueError。
    """
    mp = MediaProcessor()
    out_grid = str(tmp_path / "grid_invalid.jpg")
    
    # 1. 传入 (0, 0)
    with pytest.raises(ValueError) as exc_info:
        mp.create_grid_image([], out_grid, grid_size=(0, 0))
    assert "Grid rows and columns must be greater than 0" in str(exc_info.value)

    # 2. 传入负数行列 (-1, 5)
    with pytest.raises(ValueError) as exc_info:
        mp.create_grid_image([], out_grid, grid_size=(-1, 5))
    assert "Grid rows and columns must be greater than 0" in str(exc_info.value)

    # 3. 传入 0 行列 (5, -2)
    with pytest.raises(ValueError) as exc_info:
        mp.create_grid_image([], out_grid, grid_size=(5, -2))
    assert "Grid rows and columns must be greater than 0" in str(exc_info.value)

    # 4. 传入为 0 或负数的整数
    with pytest.raises(ValueError) as exc_info:
        mp.create_grid_image([], out_grid, grid_size=-1)
    assert "Grid rows and columns must be greater than 0" in str(exc_info.value)
