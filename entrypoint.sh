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

# Run fresh database setup if requested
if [ "${SETUP_FRESH_DATABASE:-0}" = "1" ]; then
	echo "Running setup_fresh_database..."
	if ! retry_cmd "setup_fresh_database" python manage.py setup_fresh_database; then
		echo "Warning: setup_fresh_database failed after retries." >&2
	fi
fi

# Run production data fix if requested
if [ "${RUN_FIX_PRODUCTION_DATA:-0}" = "1" ]; then
	echo "Running fix_production_data..."
	if ! retry_cmd "fix_production_data" python manage.py fix_production_data; then
		echo "Warning: fix_production_data failed after retries." >&2
	fi
fi

# Fix user/leave balance mismatches
if [ "${FIX_USER_MISMATCHES:-0}" = "1" ]; then
	echo "Running fix_user_mismatches..."
	if ! retry_cmd "fix_user_mismatches" python manage.py fix_user_mismatches; then
		echo "Warning: fix_user_mismatches failed after retries." >&2
	fi
fi

# Optionally run production data setup (idempotent). This is controlled by:
# - RUN_SEED_ON_DEPLOY=1 OR presence of DJANGO_SUPERUSER_USERNAME, HR_ADMIN_PASSWORD, or SEED_USERS env vars.
should_seed=0
if [ "${RUN_SEED_ON_DEPLOY:-0}" = "1" ]; then
	should_seed=1
fi
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] || [ -n "${HR_ADMIN_PASSWORD:-}" ] || [ -n "${SEED_USERS:-}" ]; then
	should_seed=1
fi

if [ "$should_seed" = "1" ]; then
	echo "Running setup_production_data (seed on deploy)..."
	if ! retry_cmd "setup_production_data" python manage.py setup_production_data; then
		echo "Warning: setup_production_data failed after retries." >&2
	fi
else
	echo "Skipping setup_production_data (no RUN_SEED_ON_DEPLOY and no seed env vars detected)."
fi

echo "Starting Gunicorn..."
exec gunicorn leave_management.wsgi:application --bind 0.0.0.0:${PORT:-8000}