"""llama_cpp_conversation: a chat library for llama.cpp that prefills as little as possible, so that conversations stay fast even on small machines.

Its actions are the methods of :class:`ChatWrapper`; the actions guide lists them.
"""

from .cache_context import TOOL_USE_TEMPLATE, CacheContext
from .config import Config, DrawnSampling, Sampling
from .conversation_types import ChatFunction, ChatMessage, ChatToolCall, Conversation, GeneratedTurns
from .errors import (ArgumentTypeError, ContextOverflowError, EngineError, InternalError,
                     InvalidArgumentError, InvalidSettingError, OutOfOrderError, RefusalError,
                     TemplateRefusedError, UnsupportedError)
from .messages import QUESTION_CUT_MARK
from .tool_registry import ToolRegistry
from .tools import ToolCall, ToolCallStatus, ToolSpec
from .reply import (EVICTION_CAUSES, STOP_REASONS, TOOL_CALL_POLICIES, EvictionCause, Reply,
                    ReplyStream, Report, StopReason, ToolCallPolicy)
from .resolved_template import Capabilities
from .wrapper import ChatWrapper

__all__ = [
    "Config",
    "InvalidSettingError",
    "Sampling",
    "DrawnSampling",
    "ChatWrapper",
    "ChatMessage",
    "ChatToolCall",
    "ChatFunction",
    "Conversation",
    "GeneratedTurns",
    "RefusalError",
    "InvalidArgumentError",
    "UnsupportedError",
    "TemplateRefusedError",
    "OutOfOrderError",
    "ContextOverflowError",
    "ArgumentTypeError",
    "EngineError",
    "InternalError",
    "QUESTION_CUT_MARK",
    "Capabilities",
    "Reply",
    "ReplyStream",
    "Report",
    "EvictionCause",
    "EVICTION_CAUSES",
    "StopReason",
    "STOP_REASONS",
    "ToolCallPolicy",
    "TOOL_CALL_POLICIES",
    "ToolCall",
    "ToolCallStatus",
    "ToolSpec",
    "ToolRegistry",
    # For a cache context of one's own, ``ChatWrapper(context=...)``.
    "CacheContext",
    "TOOL_USE_TEMPLATE",
]
