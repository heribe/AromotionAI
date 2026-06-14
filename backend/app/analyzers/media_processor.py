import os
import shutil
import subprocess
from PIL import Image, ImageDraw
from app.config import settings

class MediaProcessor:
    def __init__(self, test_mode: str = None):
        self.test_mode = test_mode or os.getenv("AROMOTION_TEST_MODE", "prod")

    def _has_ffmpeg(self) -> bool:
        """
        检查系统是否安装了 ffmpeg 和 ffprobe
        """
        return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

    def preprocess_image(self, input_path: str, output_path: str = None) -> str:
        """
        图片预处理：
        1. 格式预处理 (HEIF/HEIC/WebP/AVIF 等向 JPEG 转换)
        2. 如果缺少解码器，降级使用 ffmpeg 转换标准格式
        3. 等比例缩放（限制最大边 2048px）
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")

        if output_path is None:
            base, _ = os.path.splitext(input_path)
            output_path = f"{base}_preprocessed.jpg"

        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        _, ext = os.path.splitext(input_path.lower())
        temp_standard_path = None

        # 检查是否是 HEIF/AVIF 等格式，并且尝试用 PIL 打开。
        # 如果打开失败，则尝试用 ffmpeg 转换。
        img = None
        try:
            img = Image.open(input_path)
            # 尝试做一次 verify 看看能不能读取
            img.verify()
            # verify 会把文件指针关闭，重新打开
            img = Image.open(input_path)
        except Exception:
            # 如果 PIL 打开失败，且系统中有 ffmpeg，我们尝试用 ffmpeg 将其转换为临时 jpeg
            if ext in [".heic", ".heif", ".avif", ".webp"] and self._has_ffmpeg():
                temp_standard_path = f"{output_path}.temp.jpg"
                try:
                    cmd = ["ffmpeg", "-y", "-i", input_path, temp_standard_path]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    img = Image.open(temp_standard_path)
                except Exception as e:
                    raise RuntimeError(f"Failed to convert image {input_path} using ffmpeg: {e}")
            else:
                # 如果既打不开又没 ffmpeg 或者是其它不支持的损坏格式，抛出异常
                raise RuntimeError(f"Unsupported or corrupted image format: {input_path}")

        # 进行等比例缩放（限制最大边 2048px）
        try:
            width, height = img.size
            max_side = max(width, height)
            if max_side > 2048:
                scale = 2048.0 / max_side
                new_width = max(1, int(width * scale))
                new_height = max(1, int(height * scale))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 转换为 RGB 并保存为 JPEG
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            img.save(output_path, "JPEG", quality=90)
        finally:
            if img:
                img.close()
            # 清理临时文件（对称性）
            if temp_standard_path and os.path.exists(temp_standard_path):
                try:
                    os.remove(temp_standard_path)
                except OSError:
                    pass

        return output_path

    def extract_video_frames(self, video_path: str, output_dir: str, frame_count: int) -> list[str]:
        """
        视频均匀抽帧：
        1. 使用 ffprobe 获取时长
        2. [0, duration] 区间均分生成 frame_count 个时间戳
        3. 用 ffmpeg 命令抽帧 (注意 -ss 在 -i 之前)
        4. Mock 模式/无 ffmpeg 环境下自动降级为 PIL 彩色占位图
        """
        # 边界校验
        if frame_count <= 0:
            return []

        # 生产环境缺失 ffmpeg 且非 mock 模式时抛错
        if not self._has_ffmpeg() and self.test_mode != "mock":
            raise RuntimeError("ffmpeg and ffprobe are required but not installed/found in production mode.")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        frames_paths = []
        # 判断是否走 Mock 降级
        if self.test_mode == "mock" or not self._has_ffmpeg():
            # 使用 PIL 彩色占位大图降级模拟逻辑
            for i in range(frame_count):
                img_path = os.path.join(output_dir, f"frame_{i}.jpg")
                # 绘制一张带有索引的占位彩色大图
                img = Image.new("RGB", (1920, 1080), color=(i * 30 % 255, 100 + i * 15 % 155, 150))
                draw = ImageDraw.Draw(img)
                draw.text((50, 50), f"Mock Frame {i}\nVideo: {os.path.basename(video_path)}", fill=(255, 255, 255))
                img.save(img_path, "JPEG")
                img.close()
                frames_paths.append(img_path)
            return frames_paths

        # 真实 FFmpeg 提取
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        try:
            # 1. ffprobe 提取视频时长
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ]
            result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            try:
                duration = float(result.stdout.strip())
            except ValueError as ve:
                if self.test_mode != "mock":
                    raise RuntimeError("Failed to parse video duration from ffprobe output") from ve
                duration = 10.0
        except RuntimeError:
            raise
        except Exception as e:
            if self.test_mode != "mock":
                raise e
            # 如果 ffprobe 失败，降级为默认 10.0 秒或者用 mock
            duration = 10.0

        # 2. 计算均匀时间戳
        if frame_count <= 1:
            timestamps = [duration / 2.0]
        else:
            step = duration / (frame_count - 1)
            timestamps = [i * step for i in range(frame_count)]

        # 3. 循环抽帧
        for i, ts in enumerate(timestamps):
            # 防止 ts 超限
            ts = max(0.0, min(ts, duration - 0.01))
            output_frame_path = os.path.join(output_dir, f"frame_{i}.jpg")
            
            # 命令：ffmpeg -y -ss {timestamp} -i {video_path} -vframes 1 -q:v 2 {output_path}
            cmd = [
                "ffmpeg", "-y", "-ss", f"{ts:.3f}", "-i", video_path,
                "-vframes", "1", "-q:v", "2", output_frame_path
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(output_frame_path):
                    frames_paths.append(output_frame_path)
                else:
                    raise FileNotFoundError(f"ffmpeg output frame not found: {output_frame_path}")
            except Exception as e:
                # 抽帧失败
                if self.test_mode != "mock":
                    raise e
                # 降级使用一张 PIL 生成的占位图
                img = Image.new("RGB", (1920, 1080), color=(128, 128, 128))
                draw = ImageDraw.Draw(img)
                draw.text((50, 50), f"Fallback Frame {i}", fill=(255, 255, 255))
                img.save(output_frame_path, "JPEG")
                img.close()
                frames_paths.append(output_frame_path)

        return frames_paths

    def create_grid_image(self, image_paths: list[str], output_path: str, grid_size: tuple[int, int] | int = (2, 5), cell_size: int = 320) -> str:
        """
        评论者头像拼接大图：
        - 根据传入 of grid_size (rows, cols) 或者是整数动态计算行列和画布尺寸拼装大图
        - 如果是整数，按 rows=2, cols= (grid_size+1)//2 映射
        - 将图片依次 Center-Crop 居中裁剪，拼接
        - 如果传入的图片不够，则以白色背景填充
        """
        if isinstance(grid_size, int):
            grid_rows = 2
            grid_cols = (grid_size + 1) // 2
        else:
            grid_rows, grid_cols = grid_size

        if grid_rows <= 0 or grid_cols <= 0:
            raise ValueError("Grid rows and columns must be greater than 0")

        if cell_size <= 0:
            raise ValueError("Grid cell size must be greater than 0")

        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        canvas_width = grid_cols * cell_size
        canvas_height = grid_rows * cell_size

        # 创建白色画布
        grid_img = Image.new("RGB", (canvas_width, canvas_height), color=(255, 255, 255))

        for idx in range(grid_rows * grid_cols):
            row = idx // grid_cols
            col = idx % grid_cols
            x = col * cell_size
            y = row * cell_size

            # 如果索引小于传入的图片列表，则加载并裁剪拼接
            if idx < len(image_paths):
                img_path = image_paths[idx]
                if os.path.exists(img_path):
                    try:
                        with Image.open(img_path) as im:
                            # Center-Crop 居中裁剪到正方形并缩放到 cell_size
                            width, height = im.size
                            min_side = min(width, height)
                            left = (width - min_side) // 2
                            top = (height - min_side) // 2
                            cropped = im.crop((left, top, left + min_side, top + min_side))
                            resized = cropped.resize((cell_size, cell_size), Image.Resampling.LANCZOS)
                            
                            grid_img.paste(resized, (x, y))
                    except Exception:
                        # 如果打开或者读取失败，保持空白
                        pass

        # 保存图片
        grid_img.save(output_path, "JPEG", quality=90)
        grid_img.close()

        return output_path
