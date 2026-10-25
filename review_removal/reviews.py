"""Load a client's Google reviews from a CSV export, pasted text, or the
Business Profile API (see gbp_api.py), into one shape."""
import csv
import hashlib
import io
import re
from dataclasses import dataclass, field

# Header spellings seen in Business Profile exports and third-party review
# tools, mapped to our field names. Matched case- and punctuation-insensitively.
CSV_ALIASES = {
    "review_id": ["review id", "reviewid", "id", "review name", "name id"],
    "reviewer": ["reviewer", "reviewer name", "author", "author name", "name", "display name"],
    "rating": ["rating", "star rating", "stars", "score"],
    "date": ["date", "review date", "create time", "created", "published", "time"],
    "text": ["text", "review", "review text", "comment", "content", "body"],
    "url": ["url", "review url", "link"],
}

STAR_WORDS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


@dataclass
class Review:
    reviewer: str
    rating: int | None
    text: str
    date: str = ""
    url: str = ""
    review_id: str = ""
    # The Business Profile API's resource name (accounts/.../reviews/...),
    # needed to post a reply. Empty for CSV/pasted reviews.
    api_name: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.review_id:
            self.review_id = make_review_id(self.reviewer, self.date, self.text)


def make_review_id(reviewer: str, date: str, text: str) -> str:
    """Stable id for reviews that arrive without one, so the tracker can match
    the same review across imports."""
    digest = hashlib.sha1(f"{reviewer}|{date}|{text}".encode()).hexdigest()
    return f"r-{digest[:12]}"


def parse_rating(value) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.upper() in STAR_WORDS:
        return STAR_WORDS[value.upper()]
    stars = value.count("★")
    if stars:
        return stars
    match = re.search(r"\d+(\.\d+)?", value)
    if not match:
        return None
    rating = round(float(match.group()))
    return rating if 1 <= rating <= 5 else None


def _normalise(header: str) -> str:
    return re.sub(r"[^a-z]+", " ", header.lower()).strip()


def _column_map(headers):
    normalised = {_normalise(h): h for h in headers}
    mapping = {}
    for fieldname, aliases in CSV_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                mapping[fieldname] = normalised[alias]
                break
    if "text" not in mapping:
        raise ValueError(
            "CSV has no review text column. Expected one of: "
            + ", ".join(CSV_ALIASES["text"]) + f". Found: {', '.join(headers)}"
        )
    return mapping


def load_csv(source) -> list[Review]:
    """source: a path, or an open text file."""
    if isinstance(source, str):
        with open(source, newline="", encoding="utf-8-sig") as f:
            return load_csv(f)
    reader = csv.DictReader(source)
    mapping = _column_map(reader.fieldnames or [])
    used = set(mapping.values())
    reviews = []
    for row in reader:
        get = lambda name: (row.get(mapping[name]) or "").strip() if name in mapping else ""
        reviews.append(Review(
            reviewer=get("reviewer") or "Anonymous",
            rating=parse_rating(get("rating")),
            text=get("text"),
            date=get("date"),
            url=get("url"),
            review_id=get("review_id"),
            extra={k: v for k, v in row.items() if k not in used and v},
        ))
    return reviews


_KEY_LINE = re.compile(r"^(reviewer|name|rating|stars|date|url|id|review id)\s*:\s*(.*)$", re.I)


def parse_pasted(text: str) -> list[Review]:
    """Reviews pasted as blocks separated by a line of `---` (or by blank
    lines when no `---` is used). Each block may start with `Key: value`
    lines -- Reviewer, Rating, Date, URL, ID -- and the rest is the review
    text. A line of stars (e.g. ★☆☆☆☆) is read as the rating."""
    if re.search(r"^\s*-{3,}\s*$", text, re.M):
        blocks = re.split(r"^\s*-{3,}\s*$", text, flags=re.M)
    else:
        blocks = re.split(r"\n\s*\n", text)
    reviews = []
    for block in blocks:
        fields, body = {}, []
        for line in block.strip().splitlines():
            key_match = _KEY_LINE.match(line.strip())
            if key_match and not body:
                fields[key_match.group(1).lower()] = key_match.group(2).strip()
            elif re.fullmatch(r"\s*[★☆]{1,5}\s*", line) and not body and "rating" not in fields:
                fields["rating"] = line
            else:
                body.append(line)
        body_text = "\n".join(body).strip()
        if not body_text and not fields:
            continue
        reviews.append(Review(
            reviewer=fields.get("reviewer") or fields.get("name") or "Anonymous",
            rating=parse_rating(fields.get("rating") or fields.get("stars")),
            text=body_text,
            date=fields.get("date", ""),
            url=fields.get("url", ""),
            review_id=fields.get("id") or fields.get("review id") or "",
        ))
    return reviews


def load_reviews(path: str) -> list[Review]:
    """CSV if the file looks like one, pasted text otherwise."""
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    if path.lower().endswith(".csv"):
        return load_csv(io.StringIO(content))
    return parse_pasted(content)
