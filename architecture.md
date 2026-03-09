# Architecture

This document describes the architecture of the puppets library for Tor-based browser automation.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SessionManager                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Manages lifecycle of multiple Session instances        │   │
│  │  - Creates/adds sessions                                 │   │
│  │  - Runs sessions in parallel                             │   │
│  │  - Tracks state and results                              │   │
│  │  - Handles cleanup                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ manages
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Session                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Represents a single browser session with Tor           │   │
│  │  - Owns TorInstance and Browser                         │   │
│  │  - Provides driver for DOM manipulation                 │   │
│  │  - Handles lifecycle (start, run, cleanup)              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐
│   TorInstance    │    │     Browser      │    │    Driver     │
│  - Starts Tor    │    │  - Configures    │    │  (Selenium)   │
│  - Manages ports │    │    Chrome        │    │  - DOM access │
│  - Handles lifecycle│  │  - Routes through│   │  - Actions    │
└──────────────────┘    │    Tor           │    └───────────────┘
                        └──────────────────┘
```

## Core Components

### 1. Session

The `Session` class represents a single browser session with its own Tor instance.

**Responsibilities:**
- Manage lifecycle of Tor instance (start/stop)
- Manage lifecycle of Browser (start/stop)
- Provide access to the Selenium WebDriver for DOM manipulation
- Handle cleanup of all resources

**Key Properties:**
- `driver` - The Selenium WebDriver instance for DOM manipulation
- `session_id` - Unique identifier for this session
- `ip` - Current IP address through Tor
- `tor_instance` - The Tor instance (for advanced use)

**Key Methods:**
- `start()` - Start Tor and browser
- `navigate(url)` - Navigate to a URL
- `cleanup()` - Stop browser and Tor

**Usage:**
```python
from puppets import Session

# Create and start a session
session = Session(headless=False)
session.start()

# Get the driver for DOM manipulation
driver = session.driver

# Navigate and interact
driver.get("https://example.com")
button = driver.find_element(By.ID, "submit")
button.click()

# Cleanup when done
session.cleanup()

# Or use context manager
with Session() as session:
    driver = session.driver
    driver.get("https://example.com")
    # Automatic cleanup
```

### 2. SessionManager

The `SessionManager` class manages multiple `Session` instances.

**Responsibilities:**
- Create and track multiple Session instances
- Run sessions in parallel using thread pools
- Provide progress tracking
- Handle batch cleanup

**Key Methods:**
- `create_session(**kwargs)` - Create a new Session
- `add_session(session)` - Add an existing Session
- `run_all()` - Run all added sessions in parallel
- `run_sessions(num_sessions)` - Create and run multiple sessions
- `cleanup_all()` - Cleanup all sessions

**Usage:**
```python
from typing import List

from puppets import SessionManager, Session
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

# Create manager
manager: SessionManager = SessionManager(max_workers=5)

# Option 1: Create and run sessions programmatically
for i in range(5):
    session: Session = Session(headless=False)
    manager.add_session(session)

# Start all sessions (Tor + browser) in parallel
manager.start_all()

# Now each session has a driver - use run_action for PARALLEL execution
def click_button(driver: WebDriver) -> None:
    driver.get("https://example.com")
    driver.find_element(By.CSS_SELECTOR, "button").click()

results = manager.run_action(click_button)  # Runs in parallel!

# Or access drivers directly (sequential)
for session in manager.sessions:
    driver = session.driver
    driver.get("https://example.com")
    driver.find_element(By.CSS_SELECTOR, "button").click()

# Cleanup all
manager.cleanup_all()

# Option 2: Quick parallel run
manager = SessionManager(max_workers=5)
results = manager.run_sessions(num_sessions=5)
```

### 3. TorInstance

Manages a single Tor process.

**Responsibilities:**
- Find available ports
- Start Tor process
- Wait for Tor to be ready
- Handle cleanup

### 4. Browser

Manages the Chrome/Chromium browser with Tor proxy.

**Responsibilities:**
- Detect Chrome version
- Configure proxy to use Tor
- Start/Stop browser
- Handle ChromeDriver setup

## Design Principles

### 1. Session gives you the driver

The `Session` class gives you direct access to the Selenium WebDriver. This enables:
- Navigate to URLs
- Find and interact with elements
- Fill forms, click, scroll, drag
- Execute JavaScript
- Take screenshots
- DOM manipulation
- Any other Selenium operation

### 2. SessionManager manages Sessions

The `SessionManager` should:
- Accept `Session` instances (not just create them internally)
- Track all sessions it manages
- Provide parallel execution
- Handle batch operations

### 3. Explicit lifecycle

Users should have control over when sessions start and stop:
- `session.start()` - Start Tor and browser
- `session.cleanup()` - Stop everything
- Context managers for automatic cleanup

### 4. Separation of concerns

- **Session**: Browser + Tor lifecycle
- **SessionManager**: Multiple sessions + parallel execution
- **User code**: DOM manipulation via driver

## Example: Parallel Browser Automation

```python
from puppets import SessionManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def click_button_on_page(driver):
    """Action to perform in each browser."""
    driver.get("https://example.com")
    
    # Wait for button and click it
    button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "my-button"))
    )
    button.click()
    
    print(f"Clicked button on {driver.current_url}")

# Create manager with 5 workers
manager = SessionManager(max_workers=5)

# Create 5 sessions
sessions = []
for i in range(5):
    session = Session(headless=False)
    sessions.append(session)
    manager.add_session(session)

# Start all sessions (starts Tor + browser for each)
manager.start_all()

# Now run the action in all browsers in parallel
manager.run_action(click_button_on_page)

# Or do it manually for more control
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(click_button_on_page, s.driver) for s in sessions]
    concurrent.futures.wait(futures)

# Cleanup all
manager.cleanup_all()
```

## Current vs Proposed API

### Current (Problematic)
```python
manager = SessionManager(max_workers=5)
# Can't pass custom sessions
# Can't access drivers directly
results = manager.run_sessions(num_sessions=5, url="...", action_callback=...)
```

### Proposed (Clean)
```python
manager = SessionManager(max_workers=5)

# Create sessions with full control
for i in range(5):
    session = Session(headless=False)
    manager.add_session(session)

# Start all (Tor + browser)
manager.start_all()

# Access drivers directly for full control
for session in manager.sessions:
    session.driver.get("https://example.com")
    session.driver.find_element(By.ID, "button").click()

# Or run in parallel
manager.run_action(lambda driver: driver.get("https://example.com"))

# Cleanup
manager.cleanup_all()
```