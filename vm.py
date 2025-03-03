import random
import threading
import time
from concurrent import futures
from queue import Queue
import grpc

from generated import logic_clock_pb2
from generated import logic_clock_pb2_grpc


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


def serve_gRPC(port, message_queue):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = VMServiceServicer(message_queue)
    logic_clock_pb2_grpc.add_VMServiceServicer_to_server(servicer, server)

    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"[gRPC Server] Listening on port {port}...")

    server.wait_for_termination()


def main():
    clock_rate = random.randint(1, 6)
    print(f"[INIT] This VM's clock_rate = {clock_rate} instructions/sec")

    local_logical_clock = 0
    message_queue = Queue()
    port = 50051

    # start grpc server thread 
    server_thread = threading.Thread(
        target=serve_gRPC,
        args=(port, message_queue),
        daemon=True
    )
    server_thread.start()

    try:
        while True:
            time.sleep(1.0 / clock_rate)

            # 1) is there is something in message queue -> handle one
            if not message_queue.empty():
                msg = message_queue.get()
                # update logical clock
                local_logical_clock = max(local_logical_clock, msg["clock"]) + 1

                # TODO: log
                print(f"[RECEIVE] local_clock => {local_logical_clock}, msg_content='{msg['content']}'")
            
            # 2) if not, generate internal events 
            else:
                r = random.randint(1, 10)
                if r == 1:
                    # SEND to one machine
                    local_logical_clock += 1
                    # TODO: 
                elif r == 2:
                    local_logical_clock += 1
                    
                elif r == 3:
                    local_logical_clock += 1
                    
                else:
                    # internal events
                    local_logical_clock += 1
                    print(f"[INTERNAL] local_clock={local_logical_clock}")
    
    except KeyboardInterrupt:
        print("Shutting down the VM node...")


if __name__ == "__main__":
    main()