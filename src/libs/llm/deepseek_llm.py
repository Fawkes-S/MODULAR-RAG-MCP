"""DeepSeek provider implementation (OpenAI-compatible).

DeepSeek 在协议层兼容 OpenAI chat completions，因此这里采用“继承 + 轻量覆写”的策略，
复用 `OpenAILLM` 的输入校验、请求发送、错误包装与响应解析逻辑。
"""

from __future__ import annotations

from typing import Any

from libs.llm.openai_llm import OpenAILLM, TransportFn


class DeepSeekLLM(OpenAILLM):
    """DeepSeek 客户端实现（复用 OpenAI-compatible 主逻辑）。

    设计取舍：
    - 优点：避免重复维护一套相同协议逻辑，行为一致性更高；
    - 风险：如果 DeepSeek 协议后续出现差异，需要在子类中局部覆盖。
    """

    provider_name = "deepseek"

    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "https://api.deepseek.com/v1",
        timeout: float = 30.0,
        transport: TransportFn | None = None,
        **_: Any,
    ) -> None:
        """初始化 DeepSeek 客户端。

        Args:
            model: 模型名。
            api_key: API 密钥。
            base_url: DeepSeek 服务地址。
            timeout: 请求超时（秒）。
            transport: 可注入传输函数，便于测试 mock。
            **_: 兼容工厂透传的多余参数，防止非关键字段触发构造失败。
        """
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            transport=transport,
        )
