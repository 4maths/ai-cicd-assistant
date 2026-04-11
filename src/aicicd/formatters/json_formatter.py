import json
import enum
from dataclasses import asdict
from aicicd.domain.results import BaseResult

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value
        return super().default(obj)

def format_json(result: BaseResult) -> str:
    """Chuyển đổi Result objects thành JSON string đẹp mắt."""
    data = asdict(result)
    return json.dumps(data, indent=2, cls=EnumEncoder)
