"""Loader 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.types import Document


class BaseLoader(ABC):
    """文档加载器抽象基类。

    约定：
    - 输入为文件路径；
    - 输出为统一 `Document` 对象；
    - 不负责 chunk 切分与向量化。
    """

    @staticmethod
    def _validate_file(file_path: str | Path) -> Path:
        """校验输入文件路径是否存在且可读。

        Args:
            file_path: 待校验的文件路径（字符串或 Path 对象）。

        Returns:
            Path: 规范化后的绝对路径对象。

        Raises:
            FileNotFoundError: 路径不存在或不是常规文件。
            PermissionError: 文件存在但当前进程无读取权限。
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"file not found: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"not a regular file: {path}")

        try:
            with path.open("rb"):
                pass
        except OSError as exc:
            raise PermissionError(f"file is not readable: {path}") from exc

        return path.resolve()

    @abstractmethod
    def load(self, path: str) -> Document:
        """加载文件并返回标准化 Document。"""
        raise NotImplementedError
