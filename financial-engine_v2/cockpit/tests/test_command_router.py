"""Tests for cockpit.core.command_router."""

from cockpit.core.command_router import route_command


class TestWatchYoutubeChannelCommandRoute:
    def test_watch_youtube_from(self):
        r = route_command("watch youtube videos from Kneppy Invests")
        assert r.matched is True
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

    def test_unrelated_does_not_match(self):
        r = route_command("what do you think about BHP")
        assert r.matched is False

    def test_ingest_ticker_still_works(self):
        r = route_command("ingest BHP news")
        assert r.matched is True
        assert r.tool == "run_news_ingest"
