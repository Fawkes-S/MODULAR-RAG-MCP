"""Vision LLM abstraction contracts used by the project.

目标：
- 统一文本+图片输入接口，供 ImageCaptioner 等上层模块依赖；
- 为后续图片压缩/格式转换预留扩展点；
- 与具体 provider（Azure/OpenAI/本地）解耦。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChatResponse:
    """Vision LLM 输出结构。

    Attributes:
        content: 模型返回的主文本内容。
        metadata: 附加信息（tokens、model、trace tags 等），默认可为空字典。
    """

    content: str
    metadata: dict[str, Any]


class BaseVisionLLM(ABC):
    """Vision LLM 抽象接口。

    约定：
    - 输入包含文本提示 + 图片输入（本地路径或 bytes）；
    - 输出使用结构化 `ChatResponse`；
    - 图片预处理步骤独立为可重写方法，便于 provider 自定义压缩策略。
    """

    @abstractmethod
    def chat_with_image(
        self,
        text: str,
        image_path: str | bytes,
        trace: Any | None = None,
    ) -> ChatResponse:
        """执行图文对话。"""
        raise NotImplementedError

    def preprocess_image_input(self, image_path: str | bytes) -> str | bytes:
        """图片输入预处理扩展点。

        默认行为为直通；子类可覆盖以实现：
        - 图片压缩
        - 格式转换
        - 路径校验与统一编码
        """
        return image_path
