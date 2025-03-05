import json
import random
import threading
import time
from concurrent import futures
from queue import Queue
import grpc

from tools import get_peers, send_message_to_peer, log_event
import logic_clock_pb2
import logic_clock_pb2_grpc

class VMServiceServicer(logic_clock_pb2_grpc.VMServiceServicer):
    def __init__(self, message_queue):
        self.message_queue = message_queue

    def SendMessage(self, request, context):

        message = {
            "clock": request.clock,
            "content": request.content
        }

        self.message_queue.put(message)

        return logic_clock_pb2.MessageReply(status="OK")


def serve_gRPC(port, message_queue, vm_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = VMServiceServicer(message_queue)
    logic_clock_pb2_grpc.add_VMServiceServicer_to_server(servicer, server)

    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"[{vm_name}] gRPC Server listening on port {port}")

    server.wait_for_termination()


def vm_main(vm_config):
    """
    The main function for a single VM:
      - Starts a gRPC server in a separate thread.
      - Runs the "logical clock" loop, which processes queued messages or triggers local events.
    """
    vm_name = vm_config["name"]
    port = vm_config["port"]
    clock_rate = vm_config["clock_rate"]

    peers = get_peers(vm_name, 2)

    local_logical_clock = 0

    # Thread-safe queue to store incoming messages
    message_queue = Queue()

    with open(f"{vm_name}.log", "w") as f:
        f.write("") 

    # Start the gRPC server in a separate thread
    server_thread = threading.Thread(
        target=serve_gRPC,
        args=(port, message_queue, vm_name),
        daemon=True
    )
    server_thread.start()

    print(f"[{vm_name}] Initialized with clock_rate={clock_rate} instructions/second")

    # Main loop: execute 'clock_rate' instructions per real-world second.
    try:
        while True:
            time.sleep(1.0 / clock_rate)

            # 1) If there's a message in the queue, process it
            if not message_queue.empty():
                qsize = message_queue.qsize()
                msg = message_queue.get()
                # Update logical clock: max(local, remote) + 1
                local_logical_clock = max(local_logical_clock, msg["clock"]) + 1
                log_event(vm_name, "RECEIVE", local_logical_clock, queue_length=qsize, target_peers=msg["content"])

            # 2) Otherwise, pick a random number 1-10 to decide sending or internal event
            else:
                r = random.randint(1, 10)
                if r == 1:
                    send_message_to_peer(peers[0], local_logical_clock, vm_name)
                    local_logical_clock += 1
                    log_event(vm_name, "SEND", local_logical_clock, target_peers=[peers[0]])
                elif r == 2:
                    send_message_to_peer(peers[0], local_logical_clock, vm_name)
                    local_logical_clock += 1
                    log_event(vm_name, "SEND", local_logical_clock, target_peers=[peers[1]])
                elif r == 3:
                    send_message_to_peer(peers[0], local_logical_clock, vm_name)
                    send_message_to_peer(peers[1], local_logical_clock, vm_name)
                    local_logical_clock += 1
                    log_event(vm_name, "SEND", local_logical_clock, target_peers=peers)
                else:
                    # Internal event
                    local_logical_clock += 1
                    log_event(vm_name, "INTERNAL", local_logical_clock)

    except KeyboardInterrupt:
        print(f"[{vm_name}] Shutting down...")

def main():
    with open('config.json', 'r') as f:
        config_data = json.load(f)

    # config_data["VMs"] should be a list of VM configs: 
    # [ { "name": "A", "port": 50051, "clock_rate": 2 }, ... ]
    vm_list = config_data["VMs"]

    vm_threads = []
    for vm_config in vm_list:
        t = threading.Thread(
            target=vm_main,
            args=(vm_config,),
            daemon=True
        )
        t.start()
        vm_threads.append(t)

    try:
        while True:
            time.sleep(600)
    except KeyboardInterrupt:
        print("[MAIN] Interrupted, exiting...")


if __name__ == "__main__":
    main()