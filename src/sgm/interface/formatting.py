from collections.abc import Sequence


def format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    string_rows = [[str(value) for value in row] for row in rows]
    widths = [
        max([len(header), *(len(row[index]) for row in string_rows)])
        for index, header in enumerate(headers)
    ]

    def _line(parts: Sequence[str]) -> str:
        return " | ".join(
            value.ljust(width) for value, width in zip(parts, widths, strict=True)
        )

    header_line = _line(headers)
    separator = "-+-".join("-" * width for width in widths)
    body = [_line(row) for row in string_rows] or ["(none)"]
    return "\n".join([header_line, separator, *body])
