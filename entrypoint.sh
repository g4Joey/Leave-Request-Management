#!/usr/bin/env bash
# Do not exit immediately; handle transient failures (DB not ready) with retries.
set -u

retry_cmd() {
	# Usage: retry_cmd "friendly-name" <command...>
	local name="$1"
	shift
	local max_attempts=8
	local attempt=0
	local sleep_seconds=5

	while [ $attempt -lt $max_attempts ]; do
		attempt=$((attempt + 1))
		echo "[$name] Attempt $attempt of $max_attempts..."
		# Use eval on the joined arguments so we handle commands with args
		if eval "$(printf '%s ' "$@")"; then
			echo "[$name] Succeeded"
			return 0
		fi
		echo "[$name] Failed (attempt $attempt). Retrying in ${sleep_seconds}s..."
		sleep $sleep_seconds
	done

	echo "[$name] Giving up after ${max_attempts} attempts." >&2
	return 1
}

echo "Running migrations..."
if ! retry_cmd "migrate" python manage.py migrate --noinput; then
	echo "Warning: migrations failed after retries. Proceeding to start server so the site can respond." >&2
fi

echo "Collecting static files..."
if ! retry_cmd "collectstatic" python manage.py collectstatic --noinput; then
	echo "Warning: collectstatic failed after retries. Static assets may be missing." >&2
fi

echo "Starting Gunicorn..."
exec gunicorn leave_management.wsgi:application --bind 0.0.0.0:${PORT:-8000}