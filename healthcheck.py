import urllib.request
import sys

def check_health():
    """Simple healthcheck script for Docker to ping the Gradio UI."""
    try:
        # Gradio normally responds with a 200 OK on its root path when ready
        response = urllib.request.urlopen('http://localhost:7861/', timeout=5)
        if response.status == 200:
            print("Healthcheck passed.")
            sys.exit(0)
        else:
            print(f"Healthcheck failed: HTTP {response.status}")
            sys.exit(1)
    except Exception as e:
        print(f"Healthcheck failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_health()
