import os
import sys

# Ensure src/ is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sgm.cli import app

def ensure_cli_symlink():
    """Ensure that the sgm CLI binary is linked in the user's path."""
    if not getattr(sys, 'frozen', False):
        return  # Only run when packaged inside Sigma.app

    current_dir = os.path.dirname(sys.executable)
    cli_source = os.path.join(current_dir, "sgm")

    if not os.path.exists(cli_source):
        return  # Safety check: if CLI binary is not present, do nothing

    # Primary target: /usr/local/bin/sgm
    usr_local_bin = "/usr/local/bin"
    primary_link = os.path.join(usr_local_bin, "sgm")

    # Fallback target: ~/.local/bin/sgm
    home_local_bin = os.path.expanduser("~/.local/bin")
    fallback_link = os.path.join(home_local_bin, "sgm")

    # 1. Check if primary link is already correct
    if os.path.islink(primary_link):
        try:
            if os.readlink(primary_link) == cli_source:
                return
        except OSError:
            pass

    # 2. Try to write to /usr/local/bin/sgm
    if os.path.exists(usr_local_bin) and os.access(usr_local_bin, os.W_OK):
        try:
            if os.path.exists(primary_link) or os.path.islink(primary_link):
                os.remove(primary_link)
            os.symlink(cli_source, primary_link)
            print(f"CLI link created successfully: {primary_link} -> {cli_source}")
            return
        except Exception as e:
            print(f"Warning: Failed to create primary symlink: {e}")

    # 3. Try to write to ~/.local/bin/sgm
    try:
        os.makedirs(home_local_bin, exist_ok=True)
        if os.access(home_local_bin, os.W_OK):
            if os.path.exists(fallback_link) or os.path.islink(fallback_link):
                os.remove(fallback_link)
            os.symlink(cli_source, fallback_link)
            print(f"CLI fallback link created successfully: {fallback_link} -> {cli_source}")
            return
    except Exception as e:
        print(f"Warning: Failed to create fallback symlink: {e}")

if __name__ == "__main__":
    # Ensure CLI is symlinked in path
    ensure_cli_symlink()

    # Programmatically execute the 'app' command
    app(["app"])
