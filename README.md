# tor_selenium

Automate Chrome through the Tor network with Python.  
Each run gives you a different exit IP, and you can rotate identities on the fly with a single function call.

## What it does

1. Launches a **private Tor process** on random free ports (no conflict with a system Tor).
2. Opens an **undetected Chrome** browser routed through that Tor SOCKS proxy.
3. Lets you **rotate your IP** (`NEWNYM`) and verifies the new circuit is ready before continuing.

## Prerequisites

| Dependency | Install |
|---|---|
| **Tor** | `sudo apt install tor` (Debian/Ubuntu) · `brew install tor` (macOS) · or grab the [Tor Expert Bundle](https://www.torproject.org/download/tor/) on Windows |
| **Google Chrome** | [https://www.google.com/chrome/](https://www.google.com/chrome/) |
| **Python ≥ 3.10** | [https://www.python.org/downloads/](https://www.python.org/downloads/) |

> **Note:** You no longer need to download ChromeDriver manually — `undetected-chromedriver` handles that automatically and matches it to your installed Chrome version.

## Quick start

```bash
# clone the repo
git clone https://github.com/PrimalDjinn/tor_selenium.git
cd tor_selenium

# create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

# install dependencies
pip install -r requirements.txt

# run
python tor_test.py
```

You should see output like:

```
INFO:root:starting tor  socks_port=51099  control_port=32889  binary=/usr/sbin/tor
INFO:root:first request done
INFO:root:new identity requested
INFO:root:tor ready after NEWNYM – new ip 109.70.100.2
INFO:root:second request done
```

## Usage in your own code

```python
from tor_test import launch_tor, browse_through_tor, new_identity, wait_for_tor

# start tor
tor_proc, socks_port, control_port = launch_tor()

# open a browser through tor
driver = browse_through_tor(socks_port)
driver.get("https://your-app.example.com")
driver.quit()

# rotate IP
new_identity(control_port)
ip = wait_for_tor(socks_port)
print(f"New exit IP: {ip}")

# open another browser with the new IP
driver = browse_through_tor(socks_port)
driver.get("https://your-app.example.com")
driver.quit()

# clean up
tor_proc.terminate()
```

## API reference

| Function | Description |
|---|---|
| `launch_tor(timeout=120)` | Start a Tor process on free ports. Returns `(process, socks_port, control_port)`. |
| `new_identity(control_port)` | Signal `NEWNYM` to get a fresh circuit / exit IP. |
| `check_tor_proxy(socks_port)` | Single HTTP probe through the proxy — returns the exit IP. |
| `wait_for_tor(socks_port, timeout=60)` | Poll until Tor has a working circuit, then return the IP. |
| `browse_through_tor(socks_port)` | Launch an undetected Chrome instance routed through Tor. Retries up to 3 times. |

## Troubleshooting

- **`OSError: could not start tor`** — make sure the `tor` binary is on your `PATH` (`which tor`).
- **Chrome version mismatch** — update Chrome or run `pip install -U undetected-chromedriver`.
- **Timeout waiting for circuit** — increase the `timeout` argument; slow networks may need 120 s+.
- **`SocketClosed` log messages from stem** — these are harmless; they appear when the controller connection is closed.

## License

[MIT](LICENSE)

---

> *With great power comes great responsibility.* Use this tool ethically and legally.
