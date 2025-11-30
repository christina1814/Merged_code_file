"""
Structured logging utilities for Sensei 2.0.

All services (VKIS, Authoring Studio, shared platform) should use
these helpers to ensure logs are consistent and traceable.

Log fields to always include:
- trace_id
- component (vendor|authoring|common)
- stage (crawl|parse|normalize|chunk|embed|publish|qagen|api)
- feature (high-level feature name)
- ka_code (optional KA-XXX-NNNN)
"""

from __future__ import annotations

import logging
import logging.config
import logging.handlers
import json
from typing import Any, Dict, Optional

from common.sensei_common.config import settings
from common.sensei_common.utils.tracing import TraceContext
from common.sensei_common.utils.timing import start_timer
from common.sensei_common.utils.exceptions import SenseiError
from common.sensei_common.utils.error_codes import ErrorInfo
from pathlib import Path
import yaml

_LOGGER_INITIALIZED = False
_COMPONENT_HANDLERS: Dict[str, logging.Handler] = {}


# -----------------------------------------------------------------------------
# 1. CREATE LOG DIRECTORIES
# -----------------------------------------------------------------------------
def _ensure_log_directories() -> Path:
    """
    Create log directory structure: log/{component}/
    Returns the base log directory path.
    """
    # Get the project root (configs/logging.yaml -> configs -> project root)
    config_dir = Path(settings.LOGGING_YAML).parent  # configs/
    base_dir = config_dir.parent  # project root
    log_dir = base_dir / "log"
    log_dir.mkdir(exist_ok=True)
    return log_dir


# -----------------------------------------------------------------------------
# 2. GET COMPONENT FROM LOGGER NAME
# -----------------------------------------------------------------------------
def _extract_component(logger_name: str) -> str:
    """
    Extract component name from logger name.
    
    Examples:
    - "kafka.bus.publish" -> "kafka"
    - "redis.cache.get" -> "redis"
    - "postgres.db.query" -> "postgres"
    - "vendor.normalize.html2md" -> "vendor"
    - "common.utils.hash" -> "common"
    
    Falls back to "common" if no component detected.
    """
    # Known connector components
    connector_components = [
        "kafka", "redis", "postgres", "embedding", 
        "blob", "llm", "telemetry"
    ]
    
    # Known service components
    service_components = [
        "vendor", "authoring", "common"
    ]
    
    parts = logger_name.split(".")
    if parts:
        first_part = parts[0].lower()
        if first_part in connector_components or first_part in service_components:
            return first_part
    
    # Default to "common" if no component detected
    return "common"


# -----------------------------------------------------------------------------
# 3. GET OR CREATE COMPONENT FILE HANDLER
# -----------------------------------------------------------------------------
def _get_component_file_handler(component: str) -> logging.Handler:
    """
    Get or create a file handler for a specific component.
    Creates log/{component}/app.log with rotation.
    """
    global _COMPONENT_HANDLERS
    
    if component in _COMPONENT_HANDLERS:
        return _COMPONENT_HANDLERS[component]
    
    # Ensure log directory exists
    log_dir = _ensure_log_directories()
    component_log_dir = log_dir / component
    component_log_dir.mkdir(exist_ok=True)
    
    # Create rotating file handler
    log_file = component_log_dir / "app.log"
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    
    # Use JSON formatter
    formatter = logging.Formatter(
        '{"ts": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s", '
        '"trace_id": "%(trace_id)s", "span_id": "%(span_id)s", '
        '"parent_span_id": "%(parent_span_id)s", "component": "%(component)s", '
        '"stage": "%(stage)s", "feature": "%(feature)s", '
        '"ka_code": "%(ka_code)s", "duration_ms": "%(duration_ms)s", '
        '"user_id": "%(user_id)s", "tenant_id": "%(tenant_id)s"}'
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    
    _COMPONENT_HANDLERS[component] = handler
    return handler


# -----------------------------------------------------------------------------
# 4. LOAD LOGGING.YAML (your file)
# -----------------------------------------------------------------------------
def _load_logging_yaml() -> None:
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    cfg_path = Path(settings.LOGGING_YAML)
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)

    _LOGGER_INITIALIZED = True


# -----------------------------------------------------------------------------
# 5. STANDARD CONTEXT FILTER (trace, span, feature)
# -----------------------------------------------------------------------------
class SenseiContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Ensure common context fields exist for Elastic / Logstash JSON pipeline
        attrs = [
            "trace_id", "span_id", "parent_span_id",
            "feature", "component", "stage",
            "user_id", "tenant_id", "http_method", "route",
            "ka_code", "duration_ms"
        ]
        for a in attrs:
            if not hasattr(record, a):
                setattr(record, a, None)
        return True


# -----------------------------------------------------------------------------
# 6. GET LOGGER — your original pattern + enhancements
# -----------------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with component-based file logging.
    
    Creates log files in log/{component}/app.log based on logger name.
    Also writes to console (stdout) as configured in logging.yaml.
    
    Parameters
    ----------
    name : str
        Logger name (e.g., "kafka.bus.publish", "redis.cache.get")
    
    Returns
    -------
    logging.Logger
        Configured logger with component file handler and console handler.
    """
    _load_logging_yaml()
    logger = logging.getLogger(name)
    
    # Add context filter
    if not any(isinstance(f, SenseiContextFilter) for f in logger.filters):
        logger.addFilter(SenseiContextFilter())
    
    # Extract component and add file handler
    component = _extract_component(name)
    file_handler = _get_component_file_handler(component)
    
    # Add file handler if not already added (check by handler object, not just type)
    if file_handler not in logger.handlers:
        logger.addHandler(file_handler)
    
    # Ensure logger level is set
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)
    
    return logger


# -----------------------------------------------------------------------------
# 7. bind_trace() — attach trace context into logs (your need)
# -----------------------------------------------------------------------------
def bind_trace(
    logger: logging.Logger,
    ctx: TraceContext,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    base = {
        "trace_id": ctx.trace_id,
        "span_id": ctx.span_id,
        "parent_span_id": ctx.parent_span_id,
        "component": ctx.component,
        "stage": ctx.stage,
        "feature": ctx.feature,
    }
    if extra:
        base.update(extra)
    return base


# -----------------------------------------------------------------------------
#  8. log_span() wrapper (optional for async functions)
#    Supports your developers using:
#
#     @log_span("vkis", "normalize", "html2md")
#     async def fn(...):
#         ...
# -----------------------------------------------------------------------------
import functools
from common.sensei_common.utils.timing import start_timer
from common.sensei_common.utils.exceptions import SenseiError


def log_span(component: str, stage: str, feature: str):
    """
    Decorator used in VKIS + Authoring backend tasks.
    Produces:
    - span_start
    - span_end (with duration_ms)
    - span_error (KA-code included)
    """

    def decorator(fn):
        logger = get_logger(f"{component}.{stage}.{feature}")

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            ctx: TraceContext = kwargs.get("trace_ctx") or TraceContext(
                trace_id="local-dev",
                span_id="local-span",
                parent_span_id=None,
                component=component,
                stage=stage,
                feature=feature,
            )

            timer = start_timer()

            logger.info(
                "span_start",
                extra=bind_trace(logger, ctx)
            )

            try:
                result = await fn(*args, **kwargs)

                logger.info(
                    "span_end",
                    extra=bind_trace(logger, ctx, {"duration_ms": timer.elapsed_ms})
                )

                return result

            except SenseiError as e:
                logger.error(
                    "span_error",
                    extra=bind_trace(
                        logger,
                        ctx,
                        {
                            "duration_ms": timer.elapsed_ms,
                            "ka_code": e.code,
                            "http_status": e.http_status,
                        },
                    ),
                )
                raise

            except Exception:
                logger.exception(
                    "span_exception",
                    extra=bind_trace(logger, ctx, {"duration_ms": timer.elapsed_ms}),
                )
                raise

        return wrapper

    return decorator
