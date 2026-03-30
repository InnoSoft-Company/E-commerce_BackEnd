#!/bin/bash
# ================================================
#  BLANKO Backend — Setup & Run
#  تشغيل: bash setup.sh
# ================================================
set -e

echo "📦 Installing Python packages..."
pip install -r requirements.txt

echo ""
echo "🗄️  Creating database migrations..."
python manage.py makemigrations api
python manage.py migrate

echo ""
echo "🌱 Seeding initial data..."
python seed_data.py

echo ""
echo "🚀 Starting Django server on http://localhost:8000"
echo "   API docs: http://localhost:8000/api/"
echo "   Admin:    http://localhost:8000/django-admin/"
echo ""
python manage.py runserver 0.0.0.0:8000
