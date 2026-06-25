import asyncio
import re
import unittest
from unittest.mock import patch

from mcp.server.fastmcp.exceptions import ToolError
from mcp.shared.version import LATEST_PROTOCOL_VERSION

from talkcheck.server import mcp


class SlowBusinessService:
    async def check_number(self, business_number: str):
        del business_number
        await asyncio.sleep(1)
        return {}


class PlayMcpCompatibilityTest(unittest.IsolatedAsyncioTestCase):
    def test_tools_include_required_annotations_without_chat_branding(self) -> None:
        tools = mcp._tool_manager.list_tools()

        self.assertEqual(len(tools), 3)
        for tool in tools:
            self.assertRegex(tool.name, re.compile(r"^[A-Za-z0-9_-]{1,128}$"))
            self.assertNotIn("kakao", tool.name.lower())
            self.assertNotIn("TalkCheck", tool.description)
            self.assertNotIn("톡체크", tool.description)
            self.assertNotIn("KakaoTalk", tool.description)
            self.assertNotIn("카카오톡", tool.description)
            self.assertIn("사업자 확인 도우미", tool.description)
            self.assertIsNotNone(tool.annotations)
            assert tool.annotations is not None
            self.assertIsNotNone(tool.annotations.title)
            self.assertIsInstance(tool.annotations.readOnlyHint, bool)
            self.assertIsInstance(tool.annotations.destructiveHint, bool)
            self.assertIsInstance(tool.annotations.idempotentHint, bool)
            self.assertIsInstance(tool.annotations.openWorldHint, bool)

    def test_sdk_uses_playmcp_supported_protocol(self) -> None:
        self.assertEqual(LATEST_PROTOCOL_VERSION, "2025-11-25")

    async def test_tool_times_out_before_playmcp_limit(self) -> None:
        with (
            patch("talkcheck.server.business_service", SlowBusinessService()),
            patch("talkcheck.server.playmcp_tool_timeout_seconds", 0.01),
        ):
            with self.assertRaisesRegex(ToolError, "within 3 seconds"):
                await mcp._tool_manager.call_tool(
                    "check_business_registration",
                    {"business_number": "101-81-16406"},
                )


if __name__ == "__main__":
    unittest.main()
