#!/bin/bash
# Generate SEED_USERS JSON from local/seed_users.json for production deployment

echo "🔧 Generating production user seeding configuration..."

# Read the seed users JSON and convert to single-line format for env var
if [ -f "local/seed_users.json" ]; then
    # Convert multi-line JSON to single line (remove newlines and spaces)
    SEED_USERS_JSON=$(cat local/seed_users.json | jq -c .)
    
    echo "Generated SEED_USERS environment variable:"
    echo "SEED_USERS='$SEED_USERS_JSON'"
    echo ""
    echo "Add this to your .env.production file to seed all users on deployment."
    echo ""
    echo "Users that will be created:"
    cat local/seed_users.json | jq -r '.[] | "- \(.first_name) \(.last_name) (\(.username)) - \(.role) in \(.department)"'
else
    echo "❌ local/seed_users.json not found!"
    echo "Create this file with your user data first."
fi