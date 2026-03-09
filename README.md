# Puppets

<p align="center">
  <a href="https://pypi.org/project/puppets/">
    <img src="https://img.shields.io/pypi/v/puppets.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/puppets/">
    <img src="https://img.shields.io/pypi/pyversions/puppets.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/PrimalDjinn/puppets/blob/main/LICENSE">
    <img src="https://img.shields.io/pypi/l/tor-selenium.svg" alt="License">
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

## Installation

### From PyPI (recommended)

```bash
pip install tor-selenium
```

### From source

```bash
git clone https://github.com/PrimalDjinn/tor_selenium.git
cd tor_selenium
pip install -e .
```

## Prerequisites

| Dependency | Install |
|------------|---------|
| **Tor** | `sudo apt install tor` (Debian/Ubuntu) · `brew install tor` (macOS) |
| **Google Chrome** | [https://www.google.com/chrome/](https://www.google.com/chrome/) |
| **Python ≥ 3.8** | [https://www.python.org/downloads/](https://www.python.org/downloads/) |

> **Note:** You no longer need to download ChromeDriver manually — `undetected-chromedriver` handles that automatically.

## Quick Start

### Command Line

```bash
# Run 10 parallel sessions
tor-selenium run 10

# Run 100 sessions with 20 workers
tor-selenium run 100 --workers 20

# Run in headless mode
tor-selenium run 50 --headless

# Save results to JSON
tor-selenium run 10 --output results.json
```

### As a Library

```python
from tor_selenium import Session, SessionManager

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
from tor_selenium import Session

# Basic usage - get IP and navigate
with Session() as session:
    result = session.run("https://example.com")
    print(f"IP: {result['ip']}")

# Advanced usage - control the browser directly
from selenium.webdriver.common.by import By

with Session() as session:
    session.run("https://example.com")  # Start Tor and browser
    
    # Now you have full control over the browser
    driver = session.driver
    
    # Click buttons, fill forms, scrape data, etc.
    driver.find_element(By.CSS_SELECTOR, "button").click()
    driver.get("https://another-site.com")
    
    # The session will automatically clean up when exiting the context
```

### SessionManager Class

Manage multiple parallel browser sessions.

```python
from tor_selenium import SessionManager

manager = SessionManager(
    max_workers=10,    # Maximum parallel sessions
    headless=False,    # Run browsers in headless mode
    tor_timeout=120,   # Tor startup timeout
)

# Run specific number of sessions
results = manager.run_sessions(
    num_sessions=100,
    progress_callback=lambda completed, total: print(f"{completed}/{total}")
)

# Or run continuously for a duration
results = manager.run_continuous(
    duration_seconds=3600,    # Run for 1 hour
    interval_seconds=10       # Start new session every 10 seconds
)
```

## Configuration Options

### Session Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `session_id` | str | auto-generated | Custom session identifier |
| `headless` | bool | False | Run browser without GUI |
| `tor_timeout` | int | 120 | Seconds to wait for Tor startup |

### SessionManager Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_workers` | int | 10 | Maximum parallel sessions |
| `headless` | bool | False | Run browsers without GUI |
| `tor_timeout` | int | 120 | Seconds to wait for Tor startup |

## Examples

### Basic Usage

```python
from tor_selenium import Session

# Simple single session
with Session() as session:
    result = session.run("https://httpbin.org/ip")
    print(f"My IP through Tor: {result['ip']}")
```

### Parallel Sessions

```python
from tor_selenium import SessionManager

# Run 50 sessions in parallel with 10 workers
manager = SessionManager(max_workers=10)
results = manager.run_sessions(num_sessions=50)

successful = sum(1 for r in results if r['success'])
print(f"Success rate: {successful}/50")

# Print all unique IPs
ips = [r['ip'] for r in results if r['success']]
print(f"Unique IPs: {len(set(ips))}")
```

### Custom URL and Headless Mode

```python
from tor_selenium import Session

# Headless session to a specific URL
session = Session(headless=True)
result = session.run("https://example.com")
print(f"Page title: {session._driver.title}")
session.cleanup()
```

### Continuous Session Runner

```python
from tor_selenium import SessionManager

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
black tor_selenium/
mypy tor_selenium/
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