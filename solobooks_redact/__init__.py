"""SoloBooks 客户消息脱敏库。

在保存消息前由上层调用；原文只在内存中处理，本组件不负责持久化。
"""

from .redact import redact_message

__all__ = ["redact_message"]
