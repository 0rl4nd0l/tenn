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
