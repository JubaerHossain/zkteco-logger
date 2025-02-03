import json
import logging
import os
import platform
import signal
import sys
import threading
import time
from datetime import datetime
import requests
from zk import ZK
from zk.attendance import Attendance

# Helper function to determine the base path dynamically
def get_base_path():
    """Determine the base path for the application."""
    if getattr(sys, 'frozen', False):
        # If the app is frozen (bundled by PyInstaller)
        return sys._MEIPASS
    else:
        # If running as a script
        return os.path.dirname(os.path.abspath(__file__))

# Set up logging with dynamic paths
log_dir = os.path.join(get_base_path(), "logs")
os.makedirs(log_dir, exist_ok=True)

# Configure logging to reduce I/O overhead
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "device_logs.log")),
        logging.StreamHandler()
    ]
)

# Load API URL from environment variable or use default
ATTENDANCE_API_URL = os.getenv("ATTENDANCE_API_URL", "http://127.0.0.1:8000/api/attendances")

class ZKTecoDevice:
    def __init__(self, device_data):
        self.id = device_data['id']
        self.ip = device_data['ip']
        self.name = device_data['name']
        self.status = device_data['status']
        self.password = device_data['password']
        self.zk = None
        self.conn = None
        self.failed_logs_file = os.path.join(log_dir, "failed_logs.json")  # Dynamic path for failed logs
        self.device_logs = {}
        self.lock = threading.Lock()

    def connect(self):
        """Attempt to connect to the ZKTeco device."""
        try:
            self.zk = ZK(self.ip, port=4370, timeout=5, password=self.password, force_udp=False, ommit_ping=True)
            self.conn = self.zk.connect()
            self.status = "Connected"
            logging.info(f"Connected to {self.name} ({self.ip})")
            return True
        except Exception as e:
            self.status = "Connection Failed"
            logging.error(f"Connection error {self.name}: {e}")
            return False

    def get_live_logs(self):
        """Continuously capture live logs from the device."""
        while True:
            try:
                if not self.conn and not self.connect():
                    time.sleep(10)
                    continue

                # Capture logs
                logs = self.conn.live_capture(new_timeout=10)

                # Check if logs is a generator and has values
                if logs is None:
                    time.sleep(1)  # Wait for 1 second before trying again
                    continue

                logs_captured = False
                for log in (l for l in logs if l is not None):  # Filter out None values
                    logs_captured = True
                    if isinstance(log, Attendance):
                        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # Store the log in device_logs
                        with self.lock:
                            self.device_logs[log_time] = log

                        # Send to API
                        if not self.send_log_to_api(log):
                            self.store_failed_log(log_time, log)
                    else:
                        logging.warning(f"Unknown log type: {log}")

                if not logs_captured:
                    time.sleep(1)  # Wait for 1 second before trying again

                time.sleep(1)  # Wait before the next capture cycle
            except Exception as e:
                logging.error(f"Live log error {self.name}: {e}")
                time.sleep(10)

    def send_log_to_api(self, log):
        """Send a log entry to the API."""
        try:
            headers = {
                "Content-Type": "application/json",
            }
            data = {
                "device_id": self.id,
                "user_id": log.user_id,  # Accessing using dot notation
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),  # Ensure datetime is formatted
                "status": log.status
            }

            # Sending the POST request to the API
            response = requests.post(ATTENDANCE_API_URL, json=data, headers=headers, timeout=5)
            if response.status_code == 200:
                logging.info(f"Successfully sent log to API: {log.timestamp}")
                return True
            else:
                logging.error(f"Failed to send log to API. Status Code: {response.status_code}, Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending log to API: {e}")
            return False

    def store_failed_log(self, log_time, log):
        """Store failed logs locally for retry."""
        try:
            with self.lock:
                failed_logs = {}
                if os.path.exists(self.failed_logs_file):
                    with open(self.failed_logs_file, 'r') as f:
                        failed_logs = json.load(f)
                failed_logs.setdefault(self.ip, []).append({"log_time": log_time, "log": log.__dict__})
                with open(self.failed_logs_file, 'w') as f:
                    json.dump(failed_logs, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to store log: {e}")

    def process_failed_logs(self):
        """Retry sending failed logs to the API."""
        try:
            if not os.path.exists(self.failed_logs_file):
                return

            with self.lock:
                with open(self.failed_logs_file, 'r') as f:
                    try:
                        failed_logs = json.load(f)
                    except json.JSONDecodeError:
                        logging.error(f"Failed to decode JSON from {self.failed_logs_file}, skipping processing.")
                        return  # Skip processing if the JSON is invalid

                if self.ip not in failed_logs:
                    return

                logs = failed_logs[self.ip]
                success_logs = []
                for log in logs:
                    if self.send_log_to_api(Attendance(**log["log"])):
                        success_logs.append(log)

                for log in success_logs:
                    logs.remove(log)

                if len(logs) == 0:
                    del failed_logs[self.ip]
                else:
                    failed_logs[self.ip] = logs

                with open(self.failed_logs_file, 'w') as f:
                    json.dump(failed_logs, f, indent=4)
        except Exception as e:
            logging.error(f"Failed log processing error: {e}")

    def disconnect(self):
        """Disconnect from the ZKTeco device."""
        if self.conn:
            self.conn.disconnect()
            self.status = "Disconnected"
            logging.info(f"Disconnected from {self.name}")


def load_devices():
    """Load device configurations from a JSON file."""
    try:
        config_path = os.path.join(get_base_path(), "configs", "devices.json")
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Load devices error: {e}")
        return []


def save_devices(devices):
    """Save device configurations to a JSON file."""
    try:
        config_path = os.path.join(get_base_path(), "configs", "devices.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)  # Ensure the directory exists
        with open(config_path, 'w') as f:
            json.dump(devices, f, indent=4)
    except Exception as e:
        logging.error(f"Save devices error: {e}")


def graceful_shutdown(signal, frame):
    """Handle graceful shutdown."""
    logging.info("Shutting down gracefully...")
    for device in active_devices:
        device.disconnect()
    sys.exit(0)


def install_autostart():
    """Install autostart configuration for the app."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as regkey:
                exe_path = os.path.abspath(sys.argv[0])
                winreg.SetValueEx(regkey, "ZKTecoLogger", 0, winreg.REG_SZ, f'"{exe_path}"')
        elif system == "Linux":
            service = """
[Unit]
Description=ZKTeco Logger
[Service]
ExecStart=/usr/bin/python3 "{}"
Restart=always
[Install]
WantedBy=multi-user.target
""".format(os.path.abspath(sys.argv[0]))
            service_path = "/etc/systemd/system/zkteco-logger.service"
            with open(service_path, 'w') as f:
                f.write(service)
            os.system("systemctl enable zkteco-logger.service")
            os.system("systemctl start zkteco-logger.service")
        elif system == "Darwin":
            plist = """
Label
com.zkteco.logger
ProgramArguments
{}
RunAtLoad
KeepAlive
""".format(os.path.abspath(sys.argv[0]))
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.zkteco.logger.plist")
            with open(plist_path, 'w') as f:
                f.write(plist)
            os.system(f"launchctl load {plist_path}")
        logging.info("Autostart configured.")
    except Exception as e:
        logging.error(f"Autostart setup failed: {e}")


def uninstall_autostart():
    """Remove autostart configuration for the app."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as regkey:
                winreg.DeleteValue(regkey, "ZKTecoLogger")
        elif system == "Linux":
            os.system("systemctl stop zkteco-logger.service")
            os.system("systemctl disable zkteco-logger.service")
            os.remove("/etc/systemd/system/zkteco-logger.service")
        elif system == "Darwin":
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.zkteco.logger.plist")
            os.system(f"launchctl unload {plist_path}")
            os.remove(plist_path)
        logging.info("Autostart removed.")
    except Exception as e:
        logging.error(f"Autostart removal failed: {e}")


if __name__ == "__main__":
    # Handle command-line arguments for installation/uninstallation
    if len(sys.argv) > 1:
        if sys.argv[1] == "--install":
            install_autostart()
        elif sys.argv[1] == "--uninstall":
            uninstall_autostart()
        sys.exit()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # Load devices and start threads for each device
    active_devices = [ZKTecoDevice(dev) for dev in load_devices()]
    for device in active_devices:
        device.connect()

    # Start threads for live logs
    for device in active_devices:
        thread = threading.Thread(target=device.get_live_logs, daemon=True)
        thread.start()

    # Periodically process failed logs
    def periodic_failed_logs():
        while True:
            time.sleep(3600)  # Every hour
            for device in active_devices:
                device.process_failed_logs()

    threading.Thread(target=periodic_failed_logs, daemon=True).start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        graceful_shutdown(None, None)