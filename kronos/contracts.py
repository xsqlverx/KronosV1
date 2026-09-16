"""Tool boundary: strict arguments, explicit outcomes, no implicit success."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


class ToolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class Result:
    ok: bool
    code: str
    message: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def success(message: str, **data: Any) -> Result:
    return Result(True, "ok", message, data)


def validate(value: Any, schema: dict, path: str = "arguments") -> None:
    """Validate the deliberately small JSON-schema subset used by our tools."""
    kind = schema["type"]
    valid = {
        "object": lambda: isinstance(value, dict),
        "string": lambda: isinstance(value, str),
        "integer": lambda: type(value) is int,
        "boolean": lambda: type(value) is bool,
    }[kind]()
    if not valid:
        raise ToolError("invalid_arguments", f"{path} must be {kind}.")
    if "enum" in schema and value not in schema["enum"]:
        raise ToolError("invalid_arguments", f"{path} must be one of {schema['enum']}.")
    if kind == "object":
        props = schema["properties"]
        extra = set(value) - set(props)
        missing = set(schema.get("required", [])) - set(value)
        if extra or missing:
            raise ToolError("invalid_arguments", f"{path}: unknown={sorted(extra)}, missing={sorted(missing)}.")
        for key, item in value.items():
            validate(item, props[key], f"{path}.{key}")
    elif kind == "integer":
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            raise ToolError("invalid_arguments", f"{path} is outside the allowed range.")
    elif kind == "string":
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1_000_000):
            raise ToolError("invalid_arguments", f"{path} has an invalid length.")
        if "\x00" in value:
            raise ToolError("invalid_arguments", f"{path} contains a null character.")


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Result]
    mutates: bool = False

    def declaration(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": self.parameters,
        }}


class Registry:
    def __init__(self, tools: list[Tool]):
        self.tools = {tool.name: tool for tool in tools}
        if len(self.tools) != len(tools):
            raise ValueError("Duplicate tool name")

    def declarations(self) -> list[dict]:
        return [tool.declaration() for tool in self.tools.values()]

    def execute(self, name: str, arguments: Any) -> Result:
        tool = self.tools.get(name)
        if tool is None:
            return Result(False, "unknown_tool", f"Unknown tool: {name}")
        try:
            validate(arguments, tool.parameters)
            result = tool.handler(**arguments)
            if not isinstance(result, Result):
                return Result(False, "internal_error", "Tool returned no structured result.")
            return result
        except ToolError as exc:
            return Result(False, exc.code, str(exc))
        except PermissionError:
            return Result(False, "permission_denied", "The operating system denied access. Check permissions for this terminal/application.")
        except FileNotFoundError:
            return Result(False, "not_found", "The requested file, application, or operating system utility was not found.")
        except OSError as exc:
            return Result(False, "os_error", str(exc))
        except Exception as exc:
            # Do not expose arbitrary exception text (which can contain secrets).
            return Result(False, "internal_error", f"Tool failed ({type(exc).__name__}); no success was confirmed.")


def obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def string(description: str, *, empty: bool = False, maximum: int = 4096) -> dict:
    return {"type": "string", "description": description,
            "minLength": 0 if empty else 1, "maxLength": maximum}


def integer(description: str, minimum: int = 0, maximum: int = 100) -> dict:
    return {"type": "integer", "description": description, "minimum": minimum, "maximum": maximum}
