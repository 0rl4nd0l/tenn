"""Tests for cockpit.core.command_router."""

from cockpit.core.command_router import route_command


class TestWatchYoutubeChannelCommandRoute:
    def test_check_recent_youtube_videos_from_channel(self):
        r = route_command("check youtube channel Kneppy Invests")
        assert r.matched is True
        assert r.action_type == "direct_tool"
        assert r.tool == "check_youtube_channel_recent_videos"
        assert r.arguments["channel_name"] == "Kneppy Invests"
        assert r.arguments["limit"] == 8

    def test_check_channel_for_recent_videos(self):
        r = route_command("check youtube Kneppy Invests for recent videos")
        assert r.matched is True
        assert r.tool == "check_youtube_channel_recent_videos"
        assert r.arguments["channel_name"] == "Kneppy Invests"

    def test_list_recent_videos_from_channel(self):
        r = route_command("list recent videos from @KneppyInvests")
        assert r.matched is True
        assert r.tool == "check_youtube_channel_recent_videos"
        assert r.arguments["channel_name"] == "@KneppyInvests"

    def test_watch_youtube_from(self):
        r = route_command("watch youtube videos from Kneppy Invests")
        assert r.matched is True
        assert r.action_type == "direct_tool"
        assert r.tool == "watch_youtube_channel"
        assert r.arguments["channel_name"] == "Kneppy Invests"

    def test_monitor_channel(self):
        r = route_command("monitor channel Kneppy Invests")
        assert r.matched is True
        assert r.tool == "watch_youtube_channel"
        assert r.arguments["channel_name"] == "Kneppy Invests"

    def test_add_youtube_channel(self):
        r = route_command("add youtube channel @KneppyInvests")
        assert r.matched is True
        assert r.arguments["channel_name"] == "@KneppyInvests"

    def test_subscribe_to(self):
        r = route_command("subscribe to KneppyInvests")
        assert r.matched is True
        assert r.arguments["channel_name"] == "KneppyInvests"

    def test_follow_channel(self):
        r = route_command("follow channel https://youtube.com/@KneppyInvests")
        assert r.matched is True
        assert r.arguments["channel_name"] == "https://youtube.com/@KneppyInvests"

    def test_plain_watch_ticker_does_not_route_to_youtube_channel(self):
        r = route_command("watch BHP")
        assert r.matched is False

    def test_plain_monitor_ticker_does_not_route_to_youtube_channel(self):
        r = route_command("monitor BHP")
        assert r.matched is False

    def test_plain_follow_ticker_does_not_route_to_youtube_channel(self):
        r = route_command("follow BHP")
        assert r.matched is False

    def test_unrelated_does_not_match(self):
        r = route_command("what do you think about BHP")
        assert r.matched is False

    def test_ingest_ticker_still_works(self):
        r = route_command("ingest BHP news")
        assert r.matched is True
        assert r.tool == "run_news_ingest"

    def test_analyse_ticker_remains_query_not_unmapped_action(self):
        r = route_command("analyse PPT")
        assert r.matched is False

    def test_run_analysis_ticker_remains_query_until_action_exists(self):
        r = route_command("run analysis PPT")
        assert r.matched is False

    def test_ingest_selected_youtube_video_numbers(self):
        r = route_command(
            "ingest 1 and 3",
            recent_youtube_videos=[
                {"title": "One", "webpage_url": "https://www.youtube.com/watch?v=one11111111"},
                {"title": "Two", "webpage_url": "https://www.youtube.com/watch?v=two22222222"},
                {"title": "Three", "webpage_url": "https://www.youtube.com/watch?v=thr33333333"},
            ],
        )

        assert r.matched is True
        assert r.action_type == "direct_tool"
        assert r.tool == "ingest_youtube_videos"
        assert r.arguments["urls"] == [
            "https://www.youtube.com/watch?v=one11111111",
            "https://www.youtube.com/watch?v=thr33333333",
        ]

    def test_bare_youtube_video_selection_uses_context(self):
        r = route_command(
            "first",
            recent_youtube_videos=[
                {"title": "One", "webpage_url": "https://www.youtube.com/watch?v=one11111111"},
            ],
        )

        assert r.matched is True
        assert r.tool == "ingest_youtube_videos"

    def test_youtube_video_selection_without_context_does_not_route(self):
        r = route_command("ingest 1")
        assert r.matched is False


class TestMarketMoversCommandRoute:
    def test_market_movers_routes_to_tradingview_screener(self):
        r = route_command("what were the biggest movers today")

        assert r.matched is True
        assert r.action_type == "direct_tool"
        assert r.tool == "tv_screener"
        assert r.arguments["market"] == "australia"
        assert r.arguments["mode"] == "market_movers"
        assert r.arguments["sort_by"] == "change"

    def test_market_movers_prompt_does_not_route_to_news(self):
        r = route_command("market movers today?")

        assert r.matched is True
        assert r.tool == "tv_screener"
        assert r.arguments["limit"] == 20
