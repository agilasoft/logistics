"""Pick neighbouring storage positions for one handling unit.

A handling unit that occupies more than one pallet position must land in one
block: the same site, building, zone, aisle, bay, and level, with location
codes in a row (1, then 2, then 3, then 4).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def location_code_number(location_code: Any) -> Optional[int]:
	"""Return the whole number written in a location code.

	"4", "04", and 4 all mean position 4. Codes that are not a whole number
	cannot join a row of pallet positions.
	"""
	if location_code is None or isinstance(location_code, bool):
		return None
	if isinstance(location_code, int):
		return location_code if location_code >= 0 else None
	if isinstance(location_code, float):
		if location_code.is_integer() and location_code >= 0:
			return int(location_code)
		return None
	text = str(location_code).strip()
	if text.isdigit():
		return int(text)
	return None


def list_contiguous_location_blocks(
	locations: Sequence[Dict[str, Any]],
	num_locations: int,
) -> List[List[str]]:
	"""Return neighbouring blocks, the best match first.

	Each block has ``num_locations`` storage location names ordered by
	location code. Positions qualify only when they share site, building,
	zone, aisle, bay, and level, and their location codes step by one.

	The area that contains the earliest location in ``locations`` is preferred.
	Inside that area, the lowest location codes are used first (1, 2, 3, 4
	before 5, 6, 7, 8). A complete block always wins over scattered positions.
	"""
	if num_locations < 2 or not locations:
		return []

	grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = {}
	for index, row in enumerate(locations):
		name = row.get("location")
		if not name:
			continue
		number = location_code_number(row.get("location_code"))
		if number is None:
			continue
		rank = row.get("priority_rank")
		if rank is None:
			rank = index
		key = (
			_text(row.get("site")),
			_text(row.get("building")),
			_text(row.get("zone")),
			_text(row.get("aisle")),
			_text(row.get("bay")),
			_text(row.get("level")),
		)
		grouped.setdefault(key, []).append(
			{"location": name, "number": number, "rank": rank}
		)

	blocks: List[Tuple[Any, ...]] = []
	span = num_locations - 1
	for key, rows in grouped.items():
		by_number: Dict[int, Dict[str, Any]] = {}
		for row in rows:
			current = by_number.get(row["number"])
			if current is None or row["rank"] < current["rank"]:
				by_number[row["number"]] = row
		numbers = sorted(by_number)
		# The best position in this aisle/bay/level decides which area wins.
		# Inside that area, the lowest location codes are used first.
		group_rank = min(row["rank"] for row in by_number.values())
		for start_index, start in enumerate(numbers):
			end_index = start_index + span
			if end_index >= len(numbers):
				break
			end = numbers[end_index]
			if end - start != span:
				continue
			chosen = [by_number[numbers[start_index + offset]] for offset in range(num_locations)]
			names = [item["location"] for item in chosen]
			blocks.append((group_rank, start, key, names))

	blocks.sort(key=lambda item: (item[0], item[1], item[2]))
	return [item[3] for item in blocks]


def _text(value: Any) -> str:
	if value is None:
		return ""
	return str(value)
