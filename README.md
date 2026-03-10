# Puppets

<p align="center">
  <a href="https://github.com/PrimalDjinn/puppets/releases">
    <img src="https://img.shields.io/github/v/release/PrimalDjinn/puppets?include_prereleases&label=release" alt="GitHub Release">
  </a>
  <a href="https://github.com/PrimalDjinn/puppets/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/PrimalDjinn/puppets/ci.yml?label=CI" alt="CI Status">
  </a>
  <a href="https://github.com/PrimalDjinn/puppets/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/PrimalDjinn/puppets" alt="License">
  </a>
</p>

Automate Chrome through the Tor network with Python. Each run gives you a different exit IP, and you can run hundreds of sessions in parallel.

## Features

- 🚀 **Parallel Execution** - Run multiple browser sessions concurrently
- 🔒 **Isolated Tor Instances** - Each session gets its own fresh Tor instance
- 🎭 **Undetected Browsers** - Uses `undetected-chromedriver` to avoid detection
- 🔄 **Identity Rotation** - Get new IP addresses on demand
- 🖥️ **Headless Mode** - Run browsers without GUI for better performance
- 📦 **Installable Library** - Use as a library or CLI tool

## What It Does

1. Launches a **private Tor process** on random free ports (no conflict with system Tor)
2. Opens an **undetected Chrome** browser routed through that Tor SOCKS proxy
3. Each session gets a **unique IP address** from the Tor network
4. Supports **parallel execution** for running hundreds of sessions simultaneously

## Key Features

### 🔐 Tor Integration

- **Isolated Tor Instances** - Each browser session runs through its own dedicated Tor process
- **No System Tor Conflict** - Uses random free ports, so it won't interfere with any existing Tor installation
- **Identity Rotation** - Request a new Tor identity anytime to get a fresh IP address
- **Full Tor Control** - Access Tor's control port for advanced configuration

### 🎭 Undetected Chrome

- **Bypass Detection** - Uses `undetected-chromedriver` to avoid bot detection
- **Automatic ChromeDriver** - No need to manually manage ChromeDriver versions
- **Stealth Mode** - Automatically patches Chrome to appear as a regular browser
- **Works with Chrome & Chromium** - Automatically detects your installed browser

## Use Cases

- **Web Scraping** - Extract data from websites without getting blocked or rate-limited
- **Privacy Testing** - Test your applications from different IP addresses and locations
- **Automation** - Automate browser tasks while maintaining anonymity
- **Security Research** - Conduct security assessments from different exit nodes
- **Price Monitoring** - Track prices across different regions anonymously
- **Account Management** - Manage multiple accounts with different IP addresses

## Installation

### From GitHub (latest version)

```bash
pip install git+https://github.com/PrimalDjinn/puppets.git
```

### From a specific release

```bash
# Install a specific version (e.g., v1.0.1)
pip install git+https://github.com/PrimalDjinn/puppets.git@v1.0.1
```

### From GitHub Releases

Download the `.whl` file from [Releases](https://github.com/PrimalDjinn/puppets/releases) and install it directly:

```bash
pip install puppets-1.0.0-py3-none-any.whl
```

### From source

```bash
git clone https://github.com/PrimalDjinn/puppets.git
cd puppets
pip install -e .
```

## Prerequisites

| Dependency        | Install                                                                |
| ----------------- | ---------------------------------------------------------------------- |
| **Tor**           | `sudo apt install tor` (Debian/Ubuntu) · `brew install tor` (macOS)    |
| **Google Chrome** | [https://www.google.com/chrome/](https://www.google.com/chrome/)       |
| **Python ≥ 3.9**  | [https://www.python.org/downloads/](https://www.python.org/downloads/) |

> ### 🪟 Windows users
>
> The load test tooling has first‑class support for Windows:
>
> * Chrome/Chromium is detected automatically via `PATH` or the
>   usual `Program Files` installation paths.  On Windows we also
>   query the registry, so the browser does **not** need to be on your
>   PATH as long as it was installed normally.  If you still see a
>   `ChromeNotFoundError` please install Chrome or add the binary to
>   your `PATH` (the error message points to the download link).
> * The lightweight HTTP server used for screenshot files enables
>   `SO_REUSEADDR` so you can restart the test runner without
>   waiting for sockets to time out.  If another program already has the
>   port bound we simply log an error and continue – the test run is
>   unaffected.

> **Note:** You no longer need to download ChromeDriver manually — `undetected-chromedriver` handles that automatically.

## Quick Start

### Command Line

```bash
# Run 10 parallel sessions
puppets run 10

# Run 100 sessions with 20 workers
puppets run 100 --workers 20

# Run in headless mode
puppets run 50 --headless

# Save results to JSON
puppets run 10 --output results.json
```

### As a Library

```python
from puppets import Session, SessionManager
from typing import Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver

# Single session
with Session() as session:
    result = session.run("https://example.com")
    print(f"IP: {result['ip']}")

# Multiple parallel sessions
manager = SessionManager(max_workers=10)
results = manager.run_sessions(num_sessions=50)

# Process results
for r in results:
    if r['success']:
        print(f"Session {r['session_id']}: {r['ip']}")
```

## API Reference

### Session Class

A single browser session with its own Tor instance.

```python
from typing import Optional

from puppets import Session
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

# Single session - get IP and navigate
with Session() as session:
    result = session.run("https://example.com")
    print(f"IP: {result['ip']}")

# Full control - driver access
# This gives you full access to the Selenium WebDriver
with Session() as session:
    session.start()  # Start Tor and browser

    # Now you have full control over the browser
    driver: Optional[WebDriver] = session.driver

    # Navigate to any URL
    driver.get("https://example.com")

    # Wait for and interact with elements
    button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "my-button"))
    )
    button.click()

    # Fill forms, scrape data, execute JavaScript, take screenshots, etc.
    print(f"Page title: {driver.title}")

    # The session will automatically clean up when exiting the context
```

### SessionManager Class

Manage multiple parallel browser sessions. The SessionManager accepts Session instances and gives you direct access to their drivers for full control.

```python
from typing import List

from puppets import SessionManager, Session
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

# Create a manager
manager: SessionManager = SessionManager(
    max_workers=5,    # Maximum parallel sessions
    headless=False,   # Run browsers in headless mode
    tor_timeout=120,  # Tor startup timeout
)

# You can also customize how long we wait for the browser itself to start.
# This is helpful when undetected-chromedriver hangs downloading a driver or
# when a badly‑behaving Chrome instance never responds.

session = Session(headless=False, browser_start_timeout=30)

# Create 5 sessions and add them to the manager
sessions: List[Session] = []
for i in range(5):
    session: Session = Session(headless=False)
    sessions.append(session)
    manager.add_session(session)

# Start all sessions (Tor + browser) in parallel
manager.start_all()

# Run an action on all drivers in PARALLEL using run_action
def click_button(driver: WebDriver) -> None:
    driver.get("https://example.com")
    button = driver.find_element(By.ID, "submit-btn")
    button.click()
    print(f"Clicked on {driver.current_url}")

results = manager.run_action(click_button)

# Or access drivers directly if you need sequential control
for session in manager.sessions:
    driver: WebDriver = session.driver
    driver.get("https://example.com")
    # ... more complex interactions

# Cleanup
manager.cleanup_all()
```

## Configuration Options

### Session Options

| Option        | Type | Default        | Description                     |
| ------------- | ---- | -------------- | ------------------------------- |
| `session_id`  | str  | auto-generated | Custom session identifier       |
| `headless`    | bool | False          | Run browser without GUI         |
| `tor_timeout` | int  | 120            | Seconds to wait for Tor startup |
| `browser_start_timeout` | int | 30 | Seconds to wait for Chrome/ChromeDriver to launch before failing |

### SessionManager Options

| Option        | Type | Default | Description                     |
| ------------- | ---- | ------- | ------------------------------- |
| `max_workers` | int  | 10      | Maximum parallel sessions       |
| `headless`    | bool | False   | Run browsers without GUI        |
| `tor_timeout` | int  | 120     | Seconds to wait for Tor startup |

### SessionManager.run_sessions() Options

| Option              | Type     | Default | Description                   |
| ------------------- | -------- | ------- | ----------------------------- |
| `num_sessions`      | int      | 10      | Number of sessions to run     |
| `progress_callback` | callable | None    | Callback for progress updates |

### SessionManager.run_continuous() Options

| Option             | Type | Default | Description                 |
| ------------------ | ---- | ------- | --------------------------- |
| `duration_seconds` | int  | 3600    | Total time to run sessions  |
| `interval_seconds` | int  | 10      | Time between session starts |

## Examples

### Single Session

```python
from puppets import Session

# Single session with full browser control
with Session() as session:
    result = session.run("https://httpbin.org/ip")
    print(f"My IP through Tor: {result['ip']}")
```

### Parallel Sessions

```python
from puppets import SessionManager

# Run 50 sessions in parallel with 10 workers
manager = SessionManager(max_workers=10)
results = manager.run_sessions(num_sessions=50)

successful = sum(1 for r in results if r['success'])
print(f"Success rate: {successful}/50")

# Print all unique IPs
ips = [r['ip'] for r in results if r['success']]
print(f"Unique IPs: {len(set(ips))}")
```

### Custom Actions (Full Browser Control)

```python
from puppets import SessionManager, Session
from selenium.webdriver.common.by import By
import time

# Recommended: Full control over each browser
# Create 5 sessions that each go to a page and interact with elements
manager = SessionManager(max_workers=5, headless=False)

# Create and add sessions
for i in range(5):
    session = Session(headless=False)
    manager.add_session(session)

# Start all (Tor + browser)
manager.start_all()

# Now use each driver's directly
for session in manager.sessions:
    driver = session.driver
    driver.get("https://example.com")

    # Click a button
    try:
        button = driver.find_element(By.CSS_SELECTOR, "button#click-me")
        button.click()
        print(f"Clicked button on {driver.current_url}")
    except Exception as e:
        print(f"Failed: {e}")

# Cleanup
manager.cleanup_all()
```

### Custom URL and Headless Mode

```python
from puppets import Session

# Headless session to a specific URL
session = Session(headless=True)
result = session.run("https://example.com")
print(f"Page title: {session._driver.title}")
session.cleanup()
```

### Continuous Session Runner

```python
from puppets import SessionManager

# Run sessions continuously for 1 hour
manager = SessionManager(max_workers=5, headless=True)
results = manager.run_continuous(
    duration_seconds=3600,    # 1 hour
    interval_seconds=30       # New session every 30 seconds
)
```

## Troubleshooting

### Tor Issues

- **`Tor executable not found`** - Install Tor: `sudo apt install tor` (Debian) or `brew install tor` (macOS)
- **Port already in use** - The library automatically uses free ports, but ensure no other Tor instances are running
- **Timeout waiting for circuit** - Increase `tor_timeout` parameter for slow networks

### Browser Issues

- **Chrome not found** - Install Google Chrome or Chromium
- **ChromeDriver version mismatch** - Run `pip install -U undetected-chromedriver`
- **Permission denied** - Ensure Chrome is installed in a accessible location

### Performance

- **Too many parallel sessions** - Reduce `max_workers` to avoid overwhelming system resources
- **Memory issues** - Use headless mode and ensure proper cleanup with `session.cleanup()`

## Development

### Setup Development Environment

```bash
git clone https://github.com/PrimalDjinn/tor_selenium.git
cd tor_selenium
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black puppets/ tests/
mypy puppets/
```

## License

[MIT](LICENSE)

## Credits

- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) - For making Chrome automation undetectable
- [stem](https://stem.torproject.org/) - For Tor control port interaction
- [selenium](https://www.selenium.dev/) - For browser automation

---

<p align="center">
  Made with ❤️ for privacy-conscious automation
</p>
