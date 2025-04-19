from typing import Any
from ..config import EXPECTED_COORD_DIMENSIONS

def pad_coordinate(coord_str: str) -> str:
    """Pads a coordinate string with '.0' up to EXPECTED_COORD_DIMENSIONS."""
    if not isinstance(coord_str, str):
         # Handle cases where input might not be a string
         print(f"Warning: Invalid coordinate input type '{type(coord_str)}', returning as is.")
         return coord_str

    parts = coord_str.split('.')
    # Validate parts are numeric or handle potential errors
    for part in parts:
        if not part.isdigit():
            print(f"Warning: Non-digit part '{part}' found in coordinate '{coord_str}', padding may be incorrect.")
            # Decide how to handle: raise error, return original, or continue padding?
            # For now, continue padding but log warning. Consider raising ValueError for stricter validation.

    while len(parts) < EXPECTED_COORD_DIMENSIONS:
        parts.append('0')

    # Return only the first EXPECTED_COORD_DIMENSIONS parts, joined by dots
    return '.'.join(parts[:EXPECTED_COORD_DIMENSIONS])
