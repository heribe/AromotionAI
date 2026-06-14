import os
import shutil
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
from app.analyzers.media_processor import MediaProcessor

def test_media_processor_init():
    mp = MediaProcessor()
    assert mp.test_mode in ["prod", "mock", "development"]
    
    mp_mock = MediaProcessor(test_mode="mock")
    assert mp_mock.test_mode == "mock"

def test_preprocess_image_errors(tmp_path):
    mp = MediaProcessor()
    # 1. Input path not exists
    with pytest.raises(FileNotFoundError):
        mp.preprocess_image("nonexistent_image.jpg")

    # 2. Unsupported or corrupted image format (no ffmpeg)
    bad_img_path = str(tmp_path / "bad.heic")
    with open(bad_img_path, "w") as f:
        f.write("corrupted data")
        
    with patch.object(mp, "_has_ffmpeg", return_value=False):
        with pytest.raises(RuntimeError):
            mp.preprocess_image(bad_img_path)

def test_preprocess_image_success(tmp_path):
    mp = MediaProcessor()
    # 1. Normal image without resize
    img_path = str(tmp_path / "test.jpg")
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(img_path)
    img.close()
    
    out_path = mp.preprocess_image(img_path)
    assert os.path.exists(out_path)
    assert "preprocessed" in out_path
    
    # Verify dimensions are intact
    with Image.open(out_path) as out_img:
        assert out_img.size == (100, 100)

    # 2. Large image with resize
    large_img_path = str(tmp_path / "large.jpg")
    img_large = Image.new("RGB", (4000, 2000), color="red")
    img_large.save(large_img_path)
    img_large.close()
    
    out_large_path = str(tmp_path / "large_out.jpg")
    mp.preprocess_image(large_img_path, out_large_path)
    assert os.path.exists(out_large_path)
    
    with Image.open(out_large_path) as out_img:
        assert out_img.size == (2048, 1024)  # 4000 resized to 2048, 2000 resized to 1024

def test_preprocess_image_ffmpeg_fallback(tmp_path):
    mp = MediaProcessor()
    bad_img_path = str(tmp_path / "bad.heic")
    with open(bad_img_path, "w") as f:
        f.write("corrupted data")
        
    out_path = str(tmp_path / "out.jpg")
    
    # 1. Ffmpeg conversion fails
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=Exception("Ffmpeg error")):
            with pytest.raises(RuntimeError):
                mp.preprocess_image(bad_img_path, out_path)

    # 2. Ffmpeg conversion succeeds
    def mock_subprocess_run(cmd, *args, **kwargs):
        # cmd[4] is the temp output path
        temp_out = cmd[4]
        # create a valid image at temp_out
        img = Image.new("RGB", (100, 100), color="green")
        img.save(temp_out)
        img.close()
        return MagicMock()

    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=mock_subprocess_run):
            res_path = mp.preprocess_image(bad_img_path, out_path)
            assert os.path.exists(res_path)
            with Image.open(res_path) as out_img:
                assert out_img.size == (100, 100)

def test_extract_video_frames_mock(tmp_path):
    mp = MediaProcessor(test_mode="mock")
    out_dir = str(tmp_path / "frames_mock")
    
    paths = mp.extract_video_frames("fake_video.mp4", out_dir, frame_count=3)
    assert len(paths) == 3
    for path in paths:
        assert os.path.exists(path)
        with Image.open(path) as img:
            assert img.size == (1920, 1080)

def test_extract_video_frames_real_ffmpeg(tmp_path):
    mp = MediaProcessor(test_mode="prod")
    out_dir = str(tmp_path / "frames_real")
    
    # 1. Video not found
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with pytest.raises(FileNotFoundError):
            mp.extract_video_frames("nonexistent_video.mp4", out_dir, frame_count=2)

    # 2. Success with ffprobe and ffmpeg
    video_path = str(tmp_path / "video.mp4")
    with open(video_path, "w") as f:
        f.write("fake video data")

    # Mock ffprobe output to duration 20.0
    mock_run_result = MagicMock()
    mock_run_result.stdout = "20.0\n"
    
    # Mock subprocess.run for ffmpeg frame extraction: write placeholder file
    def mock_ffmpeg_run(cmd, *args, **kwargs):
        if cmd[0] == "ffprobe":
            return mock_run_result
        elif cmd[0] == "ffmpeg":
            out_file = cmd[10] # Output file path in the ffmpeg command
            img = Image.new("RGB", (1920, 1080), color="yellow")
            img.save(out_file)
            img.close()
            return MagicMock()
        return MagicMock()

    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=mock_ffmpeg_run):
            paths = mp.extract_video_frames(video_path, out_dir, frame_count=2)
            assert len(paths) == 2
            assert os.path.exists(paths[0])
            assert os.path.exists(paths[1])

    # 3. Probe fail and ffmpeg fails (should raise Exception in prod mode)
    def mock_ffmpeg_fail_run(cmd, *args, **kwargs):
        if cmd[0] == "ffprobe":
            raise Exception("Probe failed")
        elif cmd[0] == "ffmpeg":
            raise Exception("Ffmpeg failed")
        return MagicMock()

    out_dir_fail = str(tmp_path / "frames_fail")
    with patch.object(mp, "_has_ffmpeg", return_value=True):
        with patch("subprocess.run", side_effect=mock_ffmpeg_fail_run):
            with pytest.raises(Exception):
                mp.extract_video_frames(video_path, out_dir_fail, frame_count=2)

def test_extract_video_frames_zero_boundary(tmp_path):
    mp = MediaProcessor()
    # 抽帧数 <= 0 时应该直接返回空列表 []
    paths = mp.extract_video_frames("fake.mp4", str(tmp_path / "zero"), frame_count=0)
    assert paths == []

def test_create_grid_image(tmp_path):
    mp = MediaProcessor()
    
    # Create 10 source images
    image_paths = []
    for i in range(10):
        img_path = str(tmp_path / f"avatar_{i}.jpg")
        # Generate varied aspect ratios to test center-crop
        width = 200 + i * 20
        height = 300 - i * 10
        img = Image.new("RGB", (width, height), color=(i * 20, 150, 200))
        img.save(img_path)
        img.close()
        image_paths.append(img_path)

    output_grid = str(tmp_path / "grid_out.jpg")
    res_path = mp.create_grid_image(image_paths, output_grid)
    assert os.path.exists(res_path)
    
    with Image.open(res_path) as grid:
        assert grid.size == (1600, 640)

    # Test with fewer than 10 images (fill with white background)
    output_grid_fewer = str(tmp_path / "grid_fewer.jpg")
    res_path_fewer = mp.create_grid_image(image_paths[:5], output_grid_fewer)
    assert os.path.exists(res_path_fewer)
    with Image.open(res_path_fewer) as grid:
        assert grid.size == (1600, 640)

    # Test with corrupted file
    corrupt_path = str(tmp_path / "corrupt.jpg")
    with open(corrupt_path, "w") as f:
        f.write("corrupt image data")
        
    image_paths_corrupt = [corrupt_path] + image_paths[1:]
    output_grid_corrupt = str(tmp_path / "grid_corrupt.jpg")
    res_path_corrupt = mp.create_grid_image(image_paths_corrupt, output_grid_corrupt)
    assert os.path.exists(res_path_corrupt)

def test_create_grid_image_custom_grid_size(tmp_path):
    mp = MediaProcessor()
    
    # Create 4 source images
    image_paths = []
    for i in range(4):
        img_path = str(tmp_path / f"avatar_{i}.jpg")
        img = Image.new("RGB", (100, 100), color=(100, 150, 200))
        img.save(img_path)
        img.close()
        image_paths.append(img_path)

    # Test with custom tuple (2, 2)
    output_grid_custom = str(tmp_path / "grid_custom.jpg")
    res_path = mp.create_grid_image(image_paths, output_grid_custom, grid_size=(2, 2), cell_size=200)
    assert os.path.exists(res_path)
    with Image.open(res_path) as grid:
        assert grid.size == (400, 400)
