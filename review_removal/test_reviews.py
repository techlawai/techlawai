"""Tests for reviews.py -- loading reviews from CSV and pasted text."""
import io

from reviews import load_csv, make_review_id, parse_pasted, parse_rating


class TestParseRating:
    def test_reads_numbers_star_glyphs_and_api_enums(self):
        assert parse_rating("2") == 2
        assert parse_rating("4.0 stars") == 4
        assert parse_rating("★☆☆☆☆") == 1
        assert parse_rating("THREE") == 3

    def test_out_of_range_or_blank_is_none(self):
        assert parse_rating("") is None
        assert parse_rating("9") is None
        assert parse_rating(None) is None


class TestLoadCsv:
    def test_maps_common_header_spellings(self):
        csv_text = "Author Name,Star Rating,Comment,Review Date\nBob,1,Rude staff,2026-10-01\n"
        [review] = load_csv(io.StringIO(csv_text))

        assert review.reviewer == "Bob"
        assert review.rating == 1
        assert review.text == "Rude staff"
        assert review.date == "2026-10-01"

    def test_missing_text_column_is_an_error(self):
        import pytest

        with pytest.raises(ValueError, match="no review text column"):
            load_csv(io.StringIO("Reviewer,Rating\nBob,1\n"))

    def test_review_without_id_gets_a_stable_one(self):
        csv_text = "Reviewer,Rating,Text,Date\nBob,1,Rude,2026-10-01\n"
        first = load_csv(io.StringIO(csv_text))[0].review_id
        second = load_csv(io.StringIO(csv_text))[0].review_id

        assert first == second == make_review_id("Bob", "2026-10-01", "Rude")


class TestParsePasted:
    def test_dash_separated_blocks_with_key_lines(self):
        text = """Reviewer: Ann
Rating: 1
Date: 2026-09-01
Terrible.
Never again.
---
Reviewer: Ben
★★★★★
Great!
"""
        ann, ben = parse_pasted(text)

        assert (ann.reviewer, ann.rating, ann.date) == ("Ann", 1, "2026-09-01")
        assert ann.text == "Terrible.\nNever again."
        assert (ben.reviewer, ben.rating, ben.text) == ("Ben", 5, "Great!")

    def test_blank_line_separated_blocks(self):
        reviews = parse_pasted("Bad service\n\nAwful food\n")

        assert [r.text for r in reviews] == ["Bad service", "Awful food"]
        assert all(r.reviewer == "Anonymous" for r in reviews)
