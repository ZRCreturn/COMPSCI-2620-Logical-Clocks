import json
import grpc
import string
import logic_clock_pb2
import logic_clock_pb2_grpc

vm_list = []

def init():
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


init()