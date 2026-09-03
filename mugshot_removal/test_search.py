"""Tests for search.py -- the Google Custom Search query and pagination.

The API client is stubbed (see conftest.py); no HTTP request is made.
"""
from search import find_mugshot_pages


def items(count, offset=0):
    return {
        "items": [
            {
                "title": f"Result {offset + i}",
                "link": f"https://example-site.test/{offset + i}",
                "snippet": f"Snippet {offset + i}",
            }
            for i in range(count)
        ]
    }


class TestServiceSetup:
    def test_builds_the_custom_search_client_with_the_api_key(self, fake_search):
        _, build_calls = fake_search([items(10)])

        find_mugshot_pages("Jane Public", "API-KEY", "CX-ID", num_results=10)

        assert build_calls == [
            {"name": "customsearch", "version": "v1", "developerKey": "API-KEY"}
        ]

    def test_passes_the_search_engine_id(self, fake_search):
        service, _ = fake_search([items(10)])

        find_mugshot_pages("Jane Public", "API-KEY", "CX-ID", num_results=10)

        assert service.cse().calls[0]["cx"] == "CX-ID"

    def test_query_targets_the_clients_name_and_arrest_terms(self, fake_search):
        service, _ = fake_search([items(10)])

        find_mugshot_pages("Jane Public", "API-KEY", "CX-ID", num_results=10)

        assert service.cse().calls[0]["q"] == '"Jane Public" mugshot OR arrest OR booking'

    def test_client_name_is_quoted_as_a_phrase(self, fake_search):
        # Without the quotes the API matches the words separately, which
        # returns pages about unrelated people.
        service, _ = fake_search([items(1)])

        find_mugshot_pages("Jane Q Public", "API-KEY", "CX-ID", num_results=1)

        assert service.cse().calls[0]["q"].startswith('"Jane Q Public"')


class TestResultMapping:
    def test_maps_title_link_and_snippet(self, fake_search):
        fake_search(
            [
                {
                    "items": [
                        {
                            "title": "Jane Public Arrest",
                            "link": "https://example-site.test/jane",
                            "snippet": "Booking photo",
                            "displayLink": "example-site.test",
                        }
                    ]
                }
            ]
        )

        results = find_mugshot_pages("Jane Public", "K", "CX", num_results=1)

        assert results == [
            {
                "title": "Jane Public Arrest",
                "link": "https://example-site.test/jane",
                "snippet": "Booking photo",
            }
        ]

    def test_missing_fields_become_blank(self, fake_search):
        fake_search([{"items": [{}]}])

        results = find_mugshot_pages("Jane Public", "K", "CX", num_results=1)

        assert results == [{"title": "", "link": "", "snippet": ""}]


class TestPagination:
    def test_single_page_request(self, fake_search):
        service, _ = fake_search([items(10)])

        results = find_mugshot_pages("Jane Public", "K", "CX", num_results=10)

        assert len(results) == 10
        assert len(service.cse().calls) == 1
        assert service.cse().calls[0]["start"] == 1
        assert service.cse().calls[0]["num"] == 10

    def test_pages_until_the_requested_count_is_reached(self, fake_search):
        service, _ = fake_search([items(10), items(5, offset=10)])

        results = find_mugshot_pages("Jane Public", "K", "CX", num_results=15)

        assert len(results) == 15
        calls = service.cse().calls
        assert [(call["start"], call["num"]) for call in calls] == [(1, 10), (11, 5)]

    def test_never_requests_more_than_ten_per_page(self, fake_search):
        # The API caps a page at 10 results.
        service, _ = fake_search([items(10), items(10, offset=10)])

        find_mugshot_pages("Jane Public", "K", "CX", num_results=20)

        assert all(call["num"] <= 10 for call in service.cse().calls)

    def test_stops_when_the_api_runs_out_of_results(self, fake_search):
        service, _ = fake_search([items(4), {"items": []}])

        results = find_mugshot_pages("Jane Public", "K", "CX", num_results=20)

        assert len(results) == 4
        assert len(service.cse().calls) == 2

    def test_stops_on_a_response_with_no_items_key(self, fake_search):
        fake_search([{}])

        assert find_mugshot_pages("Jane Public", "K", "CX", num_results=20) == []

    def test_returns_a_short_page_without_looping_forever(self, fake_search):
        # A page that returns fewer items than asked for, then nothing.
        service, _ = fake_search([items(3), {"items": []}])

        results = find_mugshot_pages("Jane Public", "K", "CX", num_results=10)

        assert len(results) == 3
        assert len(service.cse().calls) == 2
