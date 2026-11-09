"""
消费者侧 Agent 基类。

Description:
    消费者侧的三组 Agent（买手团 / 仲裁庭 / 直播分身）都以确定性规则为主干，
    LLM 只做锦上添花的表述优化。原因有两个：

    1. 结论必须可复现、可解释——用户看到「掉色出现 12 次」要能追溯；
    2. 本地/CI 环境常常没有配置任何模型 Key，缺 LLM 时功能不能整体不可用。

    因此这里把「尝试调用 LLM，失败就静默降级」抽成公共能力。
2026-11-09
"""

import logging
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from src.agents.base import AgentRole, BaseAgent

logger = logging.getLogger(__name__)

StateT = TypeVar("StateT", bound=BaseModel)


class ConsumerAgentBase(BaseAgent[StateT]):
    """消费者侧 Agent 基类。

    Attributes:
        _enable_llm: 是否允许调用 LLM 做增强。
    """

    def __init__(
        self,
        role: AgentRole,
        enable_llm: bool = True,
        **kwargs: Any,
    ) -> None:
        """初始化。

        Args:
            role: Agent 角色。
            enable_llm: 是否允许 LLM 增强；测试中可置 False 走纯规则路径。
            **kwargs: 透传给 BaseAgent。
        """
        super().__init__(role=role, **kwargs)
        self._enable_llm = enable_llm

    async def try_generate(
        self,
        prompt: Any,
        input_vars: dict[str, Any],
        *,
        accept: Callable[[str], bool] | None = None,
    ) -> str | None:
        """尝试调用 LLM 生成文本，失败时返回 None 由调用方走规则兜底。

        Args:
            prompt: 提示模板。
            input_vars: 模板变量。
            accept: 可选的产出校验函数，返回 False 视为无效产出。

        Returns:
            模型输出文本；不可用时返回 None。
        """
        if not self._enable_llm or prompt is None:
            return None
        try:
            text = await self.invoke_llm(prompt, input_vars)
        except Exception as exc:  # 无 API Key、网络失败、记录器异常都走降级
            logger.info("%s 的 LLM 增强不可用，降级为规则结果: %s", self.role.value, exc)
            return None

        text = (text or "").strip()
        if not text:
            return None
        if accept is not None and not accept(text):
            return None
        return text
