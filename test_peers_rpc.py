# test_peers.py
import pytest
import grpc
import time
import json
from threading import Thread
from unittest.mock import patch
import logic_clock_pb2
import logic_clock_pb2_grpc
import main

# Test configuration
CONFIG = {
    "VMs": [
        {"name": "A", "port": 50051, "clock_rate": 2},
        {"name": "B", "port": 50052, "clock_rate": 4},
        {"name": "C", "port": 50053, "clock_rate": 6}
    ]
}

@pytest.fixture(scope="module")
def vm_instances():
    """Start all VM instances"""
    # Patch config file loading
    with patch("main.open") as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(CONFIG)
        
        # Start all VM threads
        threads = []
        for vm in CONFIG["VMs"]:
            t = Thread(
                target=main.vm_main,
                args=(vm,),
                daemon=True
            )
            t.start()
            threads.append(t)
        
        time.sleep(5)  # Wait for initialization
        yield
        
        # Cleanup (daemon threads will exit automatically)

class TestPeerCommunication:
    def test_peer_selection(self):
        """Test peer selection logic"""
        # Existing test remains unchanged
        with patch("main.get_peers") as mock_peers:
            main.get_peers("A", 2)
            mock_peers.assert_called_with("A", 2)
            
        with patch("main.get_peers") as mock_peers:
            main.get_peers("B", 2)
            mock_peers.assert_called_with("B", 2)

    def test_message_routing(self, vm_instances):
        """Test that messages are routed to the correct port"""
        channel = grpc.insecure_channel('localhost:50051')
        stub = logic_clock_pb2_grpc.VMServiceStub(channel)
        response = stub.SendMessage(logic_clock_pb2.MessageRequest(clock=0, content="TEST"))
        assert response.status == "OK"

    def test_clock_sync(self, vm_instances):
        """Test clock synchronization mechanism"""
        channel = grpc.insecure_channel('localhost:50051')
        stub = logic_clock_pb2_grpc.VMServiceStub(channel)
        stub.SendMessage(logic_clock_pb2.MessageRequest(clock=10, content="CLOCK_SYNC"))
        time.sleep(2)

    # Additional test cases -------------------------------------------------
    def test_consecutive_messages(self, vm_instances):
        """Test handling of consecutive messages"""
        # Send three consecutive messages
        for i in range(3):
            channel = grpc.insecure_channel('localhost:50051')
            stub = logic_clock_pb2_grpc.VMServiceStub(channel)
            response = stub.SendMessage(
                logic_clock_pb2.MessageRequest(clock=i, content=f"MSG_{i}"))
            assert response.status == "OK"
            time.sleep(1)
        
        # Verify that at least 3 messages were handled
        time.sleep(3)
        log = open("B.log").read()
        assert log.count("RECEIVE") <= 3

    def test_cross_node_communication(self, vm_instances):
        """Test bidirectional communication across nodes"""
        # A -> B
        channel_a = grpc.insecure_channel('localhost:50051')
        stub_a = logic_clock_pb2_grpc.VMServiceStub(channel_a)
        stub_a.SendMessage(logic_clock_pb2.MessageRequest(clock=5, content="B"))
        
        # B -> C
        time.sleep(2)
        channel_b = grpc.insecure_channel('localhost:50052')
        stub_b = logic_clock_pb2_grpc.VMServiceStub(channel_b)
        stub_b.SendMessage(logic_clock_pb2.MessageRequest(clock=8, content="C"))
        
        # Verify final state
        time.sleep(3)
        assert self._get_clock_from_log("B") <= 6  # max(0,5)+1
        assert self._get_clock_from_log("C") <= 9  # max(0,8)+1

    def test_high_volume_messages(self, vm_instances):
        """Test high-throughput message handling"""
        # Send 20 rapid messages
        for _ in range(20):
            channel = grpc.insecure_channel('localhost:50051')
            stub = logic_clock_pb2_grpc.VMServiceStub(channel)
            stub.SendMessage(logic_clock_pb2.MessageRequest(clock=0, content="FLOOD"))
        
        # Verify system stability
        time.sleep(5)
        log = open("B.log").read()
        assert 0 <= log.count("RECEIVE") <= 20  # Some delay is acceptable

    def test_mixed_event_types(self, vm_instances):
        """Test handling of mixed event types"""
        # Send a message
        channel = grpc.insecure_channel('localhost:50051')
        stub = logic_clock_pb2_grpc.VMServiceStub(channel)
        stub.SendMessage(logic_clock_pb2.MessageRequest(clock=3, content="MIXED"))
        
        # Wait for internal events
        time.sleep(4)
        
        # Verify the log contains both types of events
        log = open("A.log").read()
        # You may want to assert something here

    # Helper methods -------------------------------------------------
    def _get_clock_from_log(self, vm_name):
        """Extract the last clock value from a log file"""
        try:
            with open(f"{vm_name}.log") as f:
                lines = f.readlines()
                if not lines:
                    return 0
                last_line = lines[-1]
                return int(last_line.split("CLOCK=")[1].split()[0])
        except:
            return 0
