import os
import json
import time
import grpc
import string
import logic_clock_pb2
import logic_clock_pb2_grpc

vm_list = []
vm_log_filename = {}

def init():
    os.makedirs("log", exist_ok=True)
    with open('config.json', 'r') as f:
        config_data = json.load(f)
        return config_data["VMs"]
    
def send_message_to_peer(name, clock, content = "test"):
    port = 50051
    for vm in vm_list:
        if vm[name] == name:
            port = vm[port]

    target_address = "localhost:{}".format(port)

    with grpc.insecure_channel(target_address) as channel:
        stub = logic_clock_pb2_grpc.VMServiceStub(channel)
        request = logic_clock_pb2.MessageRequest(
            clock=clock,
            content=content
        )
        response = stub.SendMessage(request)
        # print("SendMessage response:", response.status)



def get_peers(name, lenth):
    alphabet = string.ascii_uppercase

    peers = [c for c in alphabet if c != name]  
    return peers[:lenth] 


def get_next_log_filename(vm_name):
    i = 0
    filename = f"log/{vm_name}.{i}.log"
    while os.path.exists(filename):
        i += 1
        filename = f"log/{vm_name}.{i}.log"
    return filename

def log_event(vm_name, event_type, logical_clock, queue_length=None, target_peers=None):
    """Log events to a file with timestamp and relevant information"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_entry = f"{timestamp} [{vm_name}]"
    
    if event_type == "RECEIVE":
        log_entry += f" [RECEIVE] Queue Length: {queue_length}, Logical Clock: {logical_clock}"
    elif event_type == "SEND":
        peers_str = ", ".join(target_peers)
        log_entry += f" [SEND] To: {peers_str}, Logical Clock: {logical_clock}"
    elif event_type == "INTERNAL":
        log_entry += f" [INTERNAL] Logical Clock: {logical_clock}"
    
    with open(vm_log_filename[vm_name], "a") as f:
        f.write(log_entry + "\n")


init()