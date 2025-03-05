import os
import re
import glob
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Regex patterns to match the three log formats.
# We assume:
#   - INTERNAL: no sender/recipient info
#   - RECEIVE: has "from:" and "Queue Length:" fields
#   - SEND: has "To:" field

INTERNAL_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<vm>[A-Z])\] \[INTERNAL\]\s+Logical Clock: (?P<logical_clock>\d+)$'
)

RECEIVE_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<vm>[A-Z])\] \[RECEIVE\s*\]\s+from: (?P<sender>[A-Z]), Queue Length: (?P<queue_length>\d+), Logical Clock: (?P<logical_clock>\d+)$'
)

SEND_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<vm>[A-Z])\] \[SEND\s*\]\s+To: (?P<recipient>[A-Z](?:,\s*[A-Z])*)?, Logical Clock: (?P<logical_clock>\d+)$'
)

def parse_log_line(line):
    """
    Parse a single log line and extract relevant information.

    :param str line: A single line from a log file.
    :return dict: A dictionary containing the parsed log line data, or None if the line can't be parsed.
    """
    line = line.strip()
    # Try matching INTERNAL first
    m = INTERNAL_PATTERN.match(line)
    if m:
        data = m.groupdict()
        data['event_type'] = 'INTERNAL'
        data['sender'] = None
        data['recipient'] = None
        data['queue_length'] = None
    else:
        m = RECEIVE_PATTERN.match(line)
        if m:
            data = m.groupdict()
            data['event_type'] = 'RECEIVE'
            data['recipient'] = None
            data['queue_length'] = int(data['queue_length'])
        else:
            m = SEND_PATTERN.match(line)
            if m:
                data = m.groupdict()
                data['event_type'] = 'SEND'
                data['sender'] = None
                data['queue_length'] = None
                # Clean up recipient: split by comma if more than one.
                if data.get('recipient'):
                    data['recipient'] = [x.strip() for x in data['recipient'].split(',')]
            else:
                return None

    # Convert timestamp and logical clock.
    try:
        data['timestamp'] = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print("Timestamp conversion error:", e, line)
        return None
    data['logical_clock'] = int(data['logical_clock'])
    return data

def load_log_file(filepath):
    """
    Load a single log file and parse its entries.

    :param str filepath: Path to the log file to load.
    :return list: A list of dictionaries, each containing the parsed log line data.
    """
    entries = []
    with open(filepath, 'r') as f:
        for line in f:
            # Parse the line, returning None if it can't be parsed.
            parsed = parse_log_line(line)
            if parsed:
                # Add the filename to the parsed data.
                parsed['filename'] = os.path.basename(filepath)
                entries.append(parsed)
    return entries

def load_all_logs(log_directory):
    """
    Load all log files in the given directory and parse their entries.

    :param str log_directory: Directory containing the log files to load.
    :return pd.DataFrame: A Pandas DataFrame containing the parsed log line data.
    """
    file_pattern = os.path.join(log_directory, '*.log')
    all_entries = []
    for filepath in glob.glob(file_pattern):
        entries = load_log_file(filepath)
        all_entries.extend(entries)
    return pd.DataFrame(all_entries)

def analyze_log_data(df):
    # Sort by timestamp per VM and per file.
    df.sort_values(['vm', 'filename', 'timestamp'], inplace=True)

    # Calculate the difference in logical clock between consecutive events per VM & file.
    # And display descriptive statistics for clock differences for each VM.
    df['clock_diff'] = df.groupby(['vm', 'filename'])['logical_clock'].diff()
    for vm in df['vm'].unique():
        vm_df = df[df['vm'] == vm]
        print(f"\nDescriptive Statistics for VM {vm}:")
        print(vm_df['clock_diff'].describe())
    
    # For RECEIVE events, get queue length statistics for each VM.
    receive_df = df[df['event_type'] == 'RECEIVE']
    for vm in receive_df['vm'].unique():
        vm_df = receive_df[receive_df['vm'] == vm]
        print(f"\nQueue Length Statistics for VM {vm}:")
        print(vm_df['queue_length'].describe())
    
    # Plot logical clock progression over time for each VM (and file).
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {'A': 'r', 'B': 'g', 'C': 'b'}
    for vm, group in df.groupby('vm'):
        for filename, sub_group in group.groupby('filename'):
            ax.plot(sub_group['timestamp'], sub_group['logical_clock'], 
                    linestyle='-', color=colors[vm], alpha=0.3)
    ax.set_xlabel("System Time")
    ax.set_ylabel("Logical Clock Value")
    ax.set_title("Logical Clock Progression Over Time")
    ax.text(0.05, 0.95, 'A (red)', transform=ax.transAxes, color='r', ha='left')
    ax.text(0.05, 0.90, 'B (green)', transform=ax.transAxes, color='g', ha='left')
    ax.text(0.05, 0.85, 'C (blue)', transform=ax.transAxes, color='b', ha='left')
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    return df

if __name__ == "__main__":
    log_directory = "./log"  # Update with the correct log directory path.
    df = load_all_logs(log_directory)
    df = analyze_log_data(df)
    # Optionally export the aggregated data for further analysis.
    # df.to_csv(f"{log_directory}/aggregated_log_analysis.csv", index=False)
