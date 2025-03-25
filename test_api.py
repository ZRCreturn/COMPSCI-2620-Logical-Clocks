import threading
import pytest
import os
import json
import grpc
import time
from queue import Queue
from unittest.mock import MagicMock, patch

from tools import get_peers, log_event, send_message_to_peer, init
import logic_clock_pb2
import logic_clock_pb2_grpc
from main import VMServiceServicer, serve_gRPC


@pytest.fixture
def sample_vm_config():
    """Fixture for a sample VM configuration."""
    return {"name": "A", "port": 50051, "clock_rate": 2}


@pytest.fixture
def sample_peers():
    """Fixture for a predefined list of VM peers."""
    return ["B", "C"]


@pytest.fixture
def message_queue():
    """Fixture for a thread-safe message queue."""
    return Queue()


@pytest.fixture
def grpc_server(sample_vm_config, message_queue):
    """Fixture to start a gRPC server for testing."""
    server = grpc.server(grpc.local_server_credentials())
    servicer = VMServiceServicer(message_queue)
    logic_clock_pb2_grpc.add_VMServiceServicer_to_server(servicer, server)
    port = sample_vm_config["port"]
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    yield server
    server.stop(0)


def test_get_peers():
    """Tests whether get_peers correctly returns peers without including the caller."""
    peers = get_peers("A", 2)
    assert len(peers) == 2
    assert "A" not in peers  # Ensure the VM does not include itself in the peer list


def test_log_event():
    """Tests whether log_event correctly writes to a log file."""
    log_file = "A.log"
    if os.path.exists(log_file):
        os.remove(log_file)  # Remove existing log file

    log_event("A", "SEND", 5, target_peers=["B", "C"])

    assert os.path.exists(log_file)

    with open(log_file, "r") as f:
        content = f.read()
        assert "SEND" in content
        assert "Logical Clock: 5" in content
        assert "To: B, C" in content


def test_init():
    """Tests whether the init function correctly loads VM configurations."""

    vm_list = init()
    assert len(vm_list) == 3
    assert vm_list[0]["name"] == "A"
    assert vm_list[0]["port"] == 50051
    assert vm_list[0]["clock_rate"] == 2



if __name__ == "__main__":
    pytest.main()
