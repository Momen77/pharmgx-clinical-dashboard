"""
Utility Functions for Database Operations
"""

from datetime import datetime
from typing import Any, Optional, Dict


def parse_date(date_str: Any) -> Optional[datetime]:
    """Parse date string to datetime object"""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    try:
        # Try ISO format first
        return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
    except:
        try:
            # Try common formats
            from dateutil import parser
            return parser.parse(str(date_str))
        except:
            return None


def generate_variant_key(variant: Dict) -> str:
    """Generate a unique key for a variant"""
    gene = variant.get("gene", "")
    variant_id = variant.get("variant_id", "")
    rsid = variant.get("rsid", "")
    return f"{gene}:{variant_id}:{rsid}"


def safe_json_dumps(data: Any) -> Optional[str]:
    """Safely convert data to JSON string"""
    import json
    if not data:
        return None
    try:
        return json.dumps(data)
    except:
        return None

