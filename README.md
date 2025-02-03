# ZKTeco Logger

The **ZKTeco Logger** is a Python-based console application designed to connect to ZKTeco biometric devices, capture live attendance logs, and send them to a REST API. It also includes features for retrying failed log submissions and supports multiple platforms (Windows, Linux, macOS).

---

## Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Autostart Setup](#autostart-setup)
7. [Logs and Error Handling](#logs-and-error-handling)
8. [Building Executables](#building-executables)
9. [Contributing](#contributing)
10. [License](#license)

---

## Features
- Connects to multiple ZKTeco devices simultaneously.
- Captures live attendance logs and sends them to a REST API.
- Retries failed log submissions periodically.
- Stores logs locally in case of API failure.
- Supports autostart configuration for Windows, Linux, and macOS.
- Cross-platform compatibility (Windows, Linux, macOS).

---

## Prerequisites
Before using the application, ensure you have the following:
- Python 3.9 or higher installed.
- Required Python packages: `zkpy`, `requests`.
- A ZKTeco device configured with the correct IP address and password.
- A REST API endpoint to receive attendance logs (default: `http://127.0.0.1:8000/api/attendances`).

---

## Installation

### Step 1: Clone the Repository
Clone the repository to your local machine:
```bash
git clone https://github.com/JubaerHossain/zkteco-logger.git
cd zkteco-logger
```

### Step 2: Install Dependencies
Install the required Python packages:
```bash
pip install -r src/requirements.txt
```

---

## Configuration

### Device Configuration
Edit the `configs/devices.json` file to add your ZKTeco device details:
```json
[
    {
        "id": 1,
        "ip": "192.168.1.201",
        "name": "Device 1",
        "status": "Active",
        "password": "0000"
    },
    {
        "id": 2,
        "ip": "192.168.1.202",
        "name": "Device 2",
        "status": "Active",
        "password": "0000"
    }
]
```

### API Endpoint
Update the API URL in the `send_log_to_api` method of `src/main.py` if needed:
```python
url = "http://your-api-endpoint.com/api/attendances"
```

---

## Usage

### Run the Application
Start the application by running the main script:
```bash
python src/main.py
```

### Logs
- Logs are stored in the `logs/` directory:
  - `device_logs.log`: General application logs.
  - `failed_logs.json`: Failed log submissions for retry.

---

## Autostart Setup

To configure the app to start automatically on system boot, use the following commands:

### Windows
```bash
python src/main.py --install
```

### Linux
```bash
sudo python src/main.py --install
```

### macOS
```bash
python src/main.py --install
```

To remove autostart:
```bash
python src/main.py --uninstall
```

---

## Logs and Error Handling
- The application logs all activities to `logs/device_logs.log`.
- Failed log submissions are stored in `logs/failed_logs.json` and retried every hour.
- Errors during API communication or device connection are logged for debugging.

---

## Building Executables

To create standalone executables for distribution, use **PyInstaller**:

### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2: Build the Executable
For Windows:
```bash
pyinstaller --onefile --add-data "configs/devices.json;configs" --add-data "logs;logs" src/main.py
```

For Linux/macOS:
```bash
pyinstaller --onefile --add-data "configs/devices.json:configs" --add-data "logs:logs" src/main.py
```

The executable will be located in the `dist/` folder.

---

## Contributing
We welcome contributions! If you'd like to contribute, please follow these steps:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description of your changes.

---

## License
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contact
For questions or support, please contact:
- Email: jubaer01.cse@gmail.com
- GitHub: [Your GitHub Profile](https://github.com/JubaerHossain)

---

This README file provides comprehensive documentation for users and developers. You can customize it further based on your specific requirements or additional features you plan to implement.