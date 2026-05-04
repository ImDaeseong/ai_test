import socket
import struct
import unittest

import network_monitor as monitor


def _tcp_packet(payload: bytes, src: str = "10.0.0.2", dst: str = "10.0.0.3") -> bytes:
    ip_header_len = 20
    tcp_header_len = 20
    total_len = ip_header_len + tcp_header_len + len(payload)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        total_len,
        0,
        0,
        64,
        6,
        0,
        socket.inet_aton(src),
        socket.inet_aton(dst),
    )
    tcp_header = struct.pack(
        "!HHLLBBHHH",
        12345,
        80,
        0,
        0,
        5 << 4,
        0x18,
        8192,
        0,
        0,
    )
    return ip_header + tcp_header + payload


class NetworkMonitorTests(unittest.TestCase):
    def test_normalize_filters_accepts_plain_and_exe_names(self) -> None:
        self.assertEqual(
            monitor._normalize_filters(["python", "node.exe", "  "]),
            {"python", "python.exe", "node.exe"},
        )

    def test_connectable_ip_maps_wildcard_addresses(self) -> None:
        self.assertEqual(monitor._connectable_ip("0.0.0.0"), "127.0.0.1")
        self.assertEqual(monitor._connectable_ip("::"), "::1")
        self.assertEqual(monitor._connectable_ip("192.0.2.1"), "192.0.2.1")

    def test_parse_http_request_extracts_url(self) -> None:
        payload = b"GET /search?q=test HTTP/1.1\r\nHost: example.com\r\n\r\n"
        parsed = monitor._parse_http_request(_tcp_packet(payload))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["method"], "GET")
        self.assertEqual(parsed["host"], "example.com")
        self.assertEqual(parsed["url"], "http://example.com/search?q=test")

    def test_redact_url_query_masks_query_when_enabled(self) -> None:
        old_value = monitor.REDACT_URL_QUERY
        try:
            monitor.REDACT_URL_QUERY = True
            self.assertEqual(
                monitor._redact_url_query("http://example.com/search?q=test#top"),
                "http://example.com/search?REDACTED#top",
            )
        finally:
            monitor.REDACT_URL_QUERY = old_value


if __name__ == "__main__":
    unittest.main()
