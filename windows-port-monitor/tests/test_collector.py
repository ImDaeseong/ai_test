from __future__ import annotations

from collections import namedtuple

import psutil

from collector.port_collector import PortCollector
from collector.process_resolver import ProcessResolver
from config_loader import CollectorConfig


Addr = namedtuple("addr", ["ip", "port"])
Conn = namedtuple("sconn", ["fd", "family", "type", "laddr", "raddr", "status", "pid"])


class DummyResolver(ProcessResolver):
    def __init__(self) -> None:
        self.cache_ttl_seconds = 0.0

    def resolve(self, pid, stats=None):
        from models import ProcessInfo

        return ProcessInfo(pid=pid, name="python.exe", exe="C:/Python/python.exe", username="User")


def test_collector_converts_tcp_and_udp(monkeypatch):
    def fake_net_connections(kind):
        if kind == "tcp":
            return [Conn(1, 2, 1, Addr("127.0.0.1", 8080), Addr("127.0.0.1", 55000), "ESTABLISHED", 123)]
        return [Conn(2, 2, 2, Addr("0.0.0.0", 53), (), "", 456)]

    monkeypatch.setattr(psutil, "net_connections", fake_net_connections)
    collector = PortCollector(CollectorConfig(), resolver=DummyResolver())

    records, stats = collector.collect()

    assert stats.total_records == 2
    assert stats.tcp_records == 1
    assert stats.udp_records == 1
    assert records[0].protocol == "TCP"
    assert records[0].remote_port == 55000
    assert records[1].protocol == "UDP"
    assert records[1].state == "NONE"


def test_collector_handles_access_denied(monkeypatch):
    def fake_net_connections(kind):
        raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", fake_net_connections)
    collector = PortCollector(CollectorConfig(), resolver=DummyResolver())

    records, stats = collector.collect()

    assert records == []
    assert stats.access_denied == 2
