from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    fields: Optional[List[Dict[str, Any]]] = None
