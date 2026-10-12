"""Extension entry point and hook implementations.

Typically, you implement the hooks your extension intends to use here; 
however, not all hooks need to be implemented, nor are they all listed 
here. 
"""

from collections.abc import Mapping
from typing import Any

from include.extensions.manager import hookimpl
lazy from include.transport.request_handler import RequestHandler


@hookimpl
def ext_validate_config(config: Mapping[str, Any]) -> None:
    pass

@hookimpl
def ext_register_handlers() -> dict[str, type["RequestHandler"]]:
    return {}

@hookimpl
def ext_unregister_handlers() -> set[str]:
    return set()

@hookimpl
def ext_register_extension_flags() -> set[str]:
    return set()

@hookimpl
def ext_on_startup() -> None:
    pass

@hookimpl
def ext_on_shutdown() -> None:
    pass
