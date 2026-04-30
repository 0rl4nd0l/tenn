from __future__ import annotations

from cockpit.core.conversation_commands import derive_conversational_command


def test_filestats_phrase_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhp filestats") == "/filestats BHP"


def test_filestat_singular_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhpt filestat") == "/filestats BHPT"


def test_memory_phrase_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhp memory") == "/memory show BHP"


def test_show_memory_phrase_maps_to_slash_command() -> None:
    assert derive_conversational_command("show memory for rio") == "/memory show RIO"


def test_non_command_phrase_returns_none() -> None:
    assert derive_conversational_command("tell me about bhp") is None


class TestYouTubeIngestRules:
    def test_bare_youtube_watch_url_maps_to_ingest(self):
        url = "https://www.youtube.com/watch?v=UNJwgi0aW6s"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_bare_youtu_be_url_maps_to_ingest(self):
        url = "https://youtu.be/UNJwgi0aW6s"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_youtu_be_with_si_param_maps_to_ingest(self):
        url = "https://youtu.be/UNJwgi0aW6s?si=jeB30d8VCY8xjnbR"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_ingest_this_video_phrase_maps_to_ingest(self):
        url = "https://youtu.be/abc123abcde"
        result = derive_conversational_command(f"ingest this video {url}")
        assert result == f"/ingest {url}"

    def test_non_youtube_url_does_not_match(self):
        result = derive_conversational_command("https://example.com/page")
        assert result is None

    def test_slash_command_passthrough_not_matched(self):
        result = derive_conversational_command("/ingest https://youtu.be/abc123abcde")
        assert result is None


class TestHoldingsConversationalCommands:
    """P3 of the cockpit verbal market updates plus holdings v1.

    Maps natural-language phrases for the cockpit-local holdings state to
    /holdings slash commands. The actual handlers live in app.py (P4).
    """

    # --- list -------------------------------------------------------------
    def test_show_holdings_maps_to_list(self) -> None:
        assert derive_conversational_command("show holdings") == "/holdings list"

    def test_show_my_holdings_maps_to_list(self) -> None:
        assert derive_conversational_command("show my holdings") == "/holdings list"

    def test_list_holdings_maps_to_list(self) -> None:
        assert derive_conversational_command("list holdings") == "/holdings list"

    def test_list_my_holdings_maps_to_list(self) -> None:
        assert derive_conversational_command("list my holdings") == "/holdings list"

    def test_bare_holdings_word_maps_to_list(self) -> None:
        assert derive_conversational_command("holdings") == "/holdings list"

    def test_bare_holding_singular_maps_to_list(self) -> None:
        assert derive_conversational_command("holding") == "/holdings list"

    def test_what_are_my_holdings_maps_to_list(self) -> None:
        assert derive_conversational_command("what are my holdings") == "/holdings list"

    def test_what_stocks_am_i_holding_maps_to_list(self) -> None:
        assert derive_conversational_command("what stocks am i holding") == "/holdings list"

    def test_what_stoicks_am_i_holding_maps_to_list(self) -> None:
        assert derive_conversational_command("what stoicks am i holding") == "/holdings list"

    def test_what_r_my_holdiongs_maps_to_list(self) -> None:
        assert derive_conversational_command("what r my holdiongs") == "/holdings list"

    def test_bare_holdiongs_word_maps_to_list(self) -> None:
        assert derive_conversational_command("holdiongs") == "/holdings list"

    # --- add --------------------------------------------------------------
    def test_add_to_holdings_maps_to_add(self) -> None:
        assert derive_conversational_command("add BHP to holdings") == "/holdings add BHP"

    def test_add_to_my_holdings_normalises_ticker(self) -> None:
        assert (
            derive_conversational_command("add cba to my holdings")
            == "/holdings add CBA"
        )

    # --- remove -----------------------------------------------------------
    def test_remove_from_holdings_maps_to_remove(self) -> None:
        assert (
            derive_conversational_command("remove BHP from holdings")
            == "/holdings remove BHP"
        )

    def test_remove_from_my_holdings_normalises_ticker(self) -> None:
        assert (
            derive_conversational_command("remove cba from my holdings")
            == "/holdings remove CBA"
        )

    # --- archive ----------------------------------------------------------
    def test_archive_ticker_holding_maps_to_archive(self) -> None:
        assert (
            derive_conversational_command("archive BHP holding")
            == "/holdings archive BHP"
        )

    def test_archive_holding_ticker_maps_to_archive(self) -> None:
        assert (
            derive_conversational_command("archive holding cba")
            == "/holdings archive CBA"
        )

    # --- non-collisions with existing rules ------------------------------
    def test_add_to_watchlist_still_routes_to_watch(self) -> None:
        # Holdings rules MUST NOT eat plain watchlist additions.
        assert (
            derive_conversational_command("add BHP to watchlist") == "/watch add BHP"
        )

    def test_watch_ticker_still_routes_to_watch(self) -> None:
        assert derive_conversational_command("watch BHP") == "/watch add BHP"

    def test_show_watchlist_still_routes_to_watch_list(self) -> None:
        assert derive_conversational_command("show my watchlist") == "/watch list"

    def test_what_is_in_my_watchlist_routes_to_watch_list(self) -> None:
        assert derive_conversational_command("what is in my watchlist") == "/watch list"

    def test_what_stocks_are_in_my_watchlist_routes_to_watch_list(self) -> None:
        assert (
            derive_conversational_command("what stocks are in my watchlist")
            == "/watch list"
        )


class TestMarketUpdateConversationalCommands:
    """Maps natural-language phrases to the /market-update slash command.

    The orchestrator that runs the update lives in P5; here we only parse
    the intent and the run_type (noon | final | manual).
    """

    # --- noon -------------------------------------------------------------
    def test_noon_market_update_maps_to_noon(self) -> None:
        assert (
            derive_conversational_command("noon market update")
            == "/market-update noon"
        )

    def test_noon_update_short_form_maps_to_noon(self) -> None:
        assert (
            derive_conversational_command("noon update") == "/market-update noon"
        )

    def test_run_noon_market_update_maps_to_noon(self) -> None:
        assert (
            derive_conversational_command("run noon market update")
            == "/market-update noon"
        )

    # --- final ------------------------------------------------------------
    def test_final_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("final market update")
            == "/market-update final"
        )

    def test_final_update_short_form_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("final update") == "/market-update final"
        )

    def test_eod_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("eod market update")
            == "/market-update final"
        )

    def test_end_of_day_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("end of day market update")
            == "/market-update final"
        )

    def test_end_hyphen_of_hyphen_day_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("end-of-day market update")
            == "/market-update final"
        )

    # --- manual -----------------------------------------------------------
    def test_manual_market_update_maps_to_manual(self) -> None:
        assert (
            derive_conversational_command("manual market update")
            == "/market-update manual"
        )

    def test_daily_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("daily market update")
            == "/market-update final"
        )

    def test_market_update_today_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("market update today?")
            == "/market-update final"
        )

    def test_todays_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("today's market update")
            == "/market-update final"
        )

    def test_what_happened_on_market_today_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("what happened on the market today")
            == "/market-update final"
        )

    # --- generic ----------------------------------------------------------
    def test_run_market_update_maps_to_final(self) -> None:
        assert (
            derive_conversational_command("run market update") == "/market-update final"
        )

    def test_bare_market_update_maps_to_final(self) -> None:
        assert derive_conversational_command("market update") == "/market-update latest"

    def test_market_update_with_question_mark_maps_to_latest(self) -> None:
        assert derive_conversational_command("market update?") == "/market-update latest"

    def test_market_updater_typo_maps_to_latest(self) -> None:
        assert derive_conversational_command("market updater") == "/market-update latest"

    # --- non-collisions ---------------------------------------------------
    def test_market_news_does_not_match(self) -> None:
        # "market news" must not be re-routed to /market-update.
        assert derive_conversational_command("show market news") is None

    def test_slash_market_update_passthrough_returns_none(self) -> None:
        assert derive_conversational_command("/market-update noon") is None
