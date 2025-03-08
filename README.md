# COMPSCI-2620-Logical-Clocks

This repository contains a simulation of a small, asynchronous distributed system that models multiple virtual machines (VMs) running at different speeds. The simulation demonstrates how logical clocks (based on Lamport’s algorithm) are used to order events in a distributed environment, even when the individual machines run at different speeds.

Each VM is implemented as a separate thread (simulating an independent machine) that:
- Operates at its own clock rate (defined in the configuration).
- Maintains a logical clock that is updated on internal events, sends, and message receives.
- Communicates with other VMs using gRPC.
- Logs events (including internal events, message sends, and message receives) to a dedicated log file.

## Repository Structure

- **config.json**  
  Defines the configuration for each virtual machine. Each VM is configured with:
  - `name`: A unique identifier (e.g., "A", "B", "C").
  - `port`: The port number on which the VM’s gRPC server listens.
  - `clock_rate`: The number of clock ticks per real-world second, which simulates different processing speeds.

- **proto/logic_clock.proto**  
  The Protocol Buffers definition file for the messages and service used in communication. It defines:
  - `MessageRequest`: Contains the sender’s logical clock and message content.
  - `MessageReply`: Used as a simple acknowledgment.
  - `VMService`: A gRPC service with a `SendMessage` method for inter-VM communication.

- **logic_clock_pb2.py** and **logic_clock_pb2_grpc.py**  
  Automatically generated Python files from `logic_clock.proto` using the Protocol Buffers compiler. They define the data structures and gRPC classes required for communication.

- **main.py**  
  The core simulation script that:
  - Reads the configuration.
  - Starts a gRPC server for each VM in a separate thread.
  - Runs the logical clock loop, which processes incoming messages from a thread-safe queue or generates random internal events/sends.
  - Logs every event with a timestamp, VM identifier, event type, logical clock value, and (if applicable) message queue length and target peers.

- **tools.py**  
  Contains helper functions, including:
  - Initialization and configuration loading.
  - Functions for sending messages between VMs (`send_message_to_peer`).
  - Peer discovery (`get_peers`).
  - Log management (generating unique log filenames and logging events).

- **log_analysis.py**  
  A Python script to parse and analyze the generated log files. It:
  - Reads log files (e.g., `A.0.log`, `B.1.log`, etc.) from the `log/` directory.
  - Parses three types of log entries: INTERNAL, RECEIVE, and SEND.
  - Computes descriptive statistics for logical clock jumps and message queue lengths.
  - Visualizes the progression of logical clock values over time.
  - Exports the aggregated data for further analysis.

- **engineering_notebook.md**  
  An engineering notebook that documents:
  - The design decisions made during the project.
  - Detailed observations and reflections from experimental runs.
  - Analysis of logical clock jumps, drift between VMs, and the impact of message queue buildup.
  - Suggestions for further experiments (e.g., varying clock rates, altering event probabilities).

## How It Works

1. **Initialization**  
   The simulation reads `config.json` to determine the VMs' names, ports, and clock rates. Each VM initializes its own log file and establishes gRPC communication with its peers.

2. **Logical Clock Updates**  
   - **Internal events:** The VM increments its logical clock by 1.
   - **Send events:** Before sending a message, the VM increments its logical clock and logs the event. The message includes the current logical clock value.
   - **Receive events:** When a message is received, the VM updates its logical clock using:
     ```
     local_logical_clock = max(local_logical_clock, received_clock) + 1
     ```
     This may result in a "jump" in the logical clock if the received value is higher than the local clock.

3. **Event Generation**  
   On each clock tick (based on its `clock_rate`), a VM either:
   - Processes a message from its queue (if available), or
   - Randomly decides (using a random integer from 1 to 10) to perform:
     - A send event (to one or more peers) for values 1, 2, or 3.
     - An internal event for values 4–10.

4. **Logging and Analysis**  
   Every event is logged with a timestamp, event type, logical clock value, and additional details (such as queue length for RECEIVE events and target peers for SEND events).  
   The `log_analysis.py` script can be run to parse these log files, compute statistics, and generate visualizations to study:
   - The size of logical clock jumps.
   - Drift in the logical clock values across different VMs.
   - Message queue lengths and their impact on clock updates.

## Running the Simulation

1. **Setup:**  
   - Ensure you have Python 3 installed.
   - Install the required packages (e.g., `grpcio`, `protobuf`, `pandas`, `matplotlib`):
     ```bash
     pip install grpcio google google-api-python-client pandas matplotlib
     ```

2. **Compile the Protobuf Files (if needed):**  
   If you make changes to `logic_clock.proto`, recompile with:
   ```bash
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. logic_clock.proto
   ```

3. **Start the Simulation:**
   Run the main simulation:
   ```bash
   python main.py
   ```
   This will start the VMs and log events in the `log/` directory.

4. **Analyze Logs:**
   After running the simulation for your desired duration (e.g., at least one minute per run), analyze the logs by executing:
   ```bash
   python log_analysis.py
   ```
   This script will generate statistics, visualizations (e.g., logical clock progression), and export aggregated data for further review.

## Engineering Notebook

Refer to `engineering_notebook.md` for detailed documentation of:

- The design decisions.
- Observations from multiple simulation runs.
- Analysis of logical clock drift, jumps, and message queue statistics.
- Reflections on how varying clock rates and event probabilities affect system behavior.

