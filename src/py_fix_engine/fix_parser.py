"""
FIX message parser utilities.

Responsibility: Purely structural parsing of raw FIX strings.
Functions: parse(), extract_tag()
"""

# Mapping of count tags to the tags that belong in each group entry.
# The first tag in the list is the "delimiter" tag that starts each entry.
GROUP_DEFS = {
    453: [448, 447, 452],  # NoPartyIDs -> PartyID, PartyIDSource, PartyRole
    73: [11, 38, 54, 55],  # NoOrders -> ClOrdID, OrderQty, Side, Symbol
}


def extract_tag(raw_str, tag_num):
    """Fast single-tag extraction from a raw FIX string.

    Returns the string value for the given tag number, or None if not found.
    """
    prefix = f"{tag_num}="
    for part in raw_str.split('\x01'):
        if part.startswith(prefix):
            return part[len(prefix):]
    return None


def parse(raw_str):
    """Parse a raw FIX string into a structured dict.

    Returns:
        {
            "tags": {int: str, ...},
            "groups": {count_tag_int: [{tag: val, ...}, ...], ...}
        }
    """
    tags = {}
    groups = {}

    parts = [p for p in raw_str.split('\x01') if p and '=' in p]

    i = 0
    while i < len(parts):
        tag_str, _, value = parts[i].partition('=')
        try:
            tag_num = int(tag_str)
        except ValueError:
            i += 1
            continue

        if tag_num in GROUP_DEFS:
            member_tags = GROUP_DEFS[tag_num]
            delimiter_tag = member_tags[0]
            count = int(value)
            entries = []
            i += 1

            for _ in range(count):
                entry = {}
                # The first tag of each entry must be the delimiter tag
                if i < len(parts):
                    dt_str, _, dt_val = parts[i].partition('=')
                    try:
                        dt_num = int(dt_str)
                    except ValueError:
                        break
                    if dt_num != delimiter_tag:
                        break
                    entry[dt_num] = dt_val
                    i += 1

                # Collect remaining member tags for this entry
                while i < len(parts):
                    nt_str, _, nt_val = parts[i].partition('=')
                    try:
                        nt_num = int(nt_str)
                    except ValueError:
                        break
                    if nt_num == delimiter_tag or nt_num not in member_tags:
                        break
                    entry[nt_num] = nt_val
                    i += 1

                entries.append(entry)

            groups[tag_num] = entries
        else:
            tags[tag_num] = value
            i += 1

    return {"tags": tags, "groups": groups}
