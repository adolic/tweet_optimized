CONDA_ENV_NAME = tweet-optimize
PYTHON_VERSION = 3.11

.PHONY: setup setup-backend setup-frontend run-backend run-frontend migrate train-models train preview-data test dev dev-down

setup: setup-backend setup-frontend

setup-backend:
	conda create -n $(CONDA_ENV_NAME) python=$(PYTHON_VERSION) -y
	conda run -n $(CONDA_ENV_NAME) pip install fastapi uvicorn python-dotenv psycopg2-binary selenium webdriver-manager beautifulsoup4 pandas tqdm

setup-frontend:
	cd frontend && npm install

# Migration commands and usage:
#   1. Create new migration:
#      make migrate cmd=create my_migration_name
#      This creates a new timestamped migration file in backend/lib/migrations/
#
#   2. Apply all pending migrations:
#      make migrate cmd=up
#
#   3. Rollback last migration:
#      make migrate cmd=down
#
# IMPORTANT: Always use 'make migrate cmd=create' to create new migrations.
# DO NOT create migration files manually to ensure correct timestamp and format.
migrate:
	conda run -n $(CONDA_ENV_NAME) python backend/migrate.py $(cmd)

# Train machine learning models for tweet predictions
# Usage: make train-models
train-models:
	conda run -n $(CONDA_ENV_NAME) python -c "from backend.model.models import Models; models = Models(['views', 'likes', 'retweets', 'comments']); models.train()"

# Direct execution of models.py with train parameter
# Usage: make train
train:
	conda run -n $(CONDA_ENV_NAME) python -m backend.model.models train

run-backend:
	conda run -n $(CONDA_ENV_NAME) uvicorn backend.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev 

# Preview database tables
# Usage: make preview-data
preview-data:
	conda run -n $(CONDA_ENV_NAME) python backend/lib/db_viewer.py 

# Start development environment with Docker Compose
# Usage: make dev
dev:
	docker-compose -f docker-compose.dev.yaml up --build

# Stop development environment and clean up
# Usage: make dev-down
dev-down:
	docker-compose -f docker-compose.dev.yaml down
