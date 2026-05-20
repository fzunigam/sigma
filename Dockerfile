FROM python:3.12-slim

WORKDIR /app

# Copy dependency definition and README
COPY pyproject.toml README.md ./

# Install python-telegram-bot and other dependencies first to leverage caching
RUN pip install --no-cache-dir ".[telegram]"

# Copy project source code
COPY src/ ./src

# Re-install project to register source changes and entrypoints
RUN pip install --no-cache-dir -e .

# Default SQLite database is at ~/.local/share/sgm/sigma.db
# Default configuration is at ~/.config/sgm/config.toml
# Under root user in container, these map to /root/
VOLUME ["/root/.config/sgm", "/root/.local/share/sgm"]

ENTRYPOINT ["sgm", "bot", "run"]
