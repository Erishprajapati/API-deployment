Project Management System
  A scalable, role-based web application designed to streamline collaboration across multi-sector organizations and distributed teams. This system addresses common challenges in cross-company project coordination by providing centralized control over employee records, departmental assignments, and task delegation.

Key Features
  Role-Based Access Control (RBAC): Granular permissions for employees, team leads, project managers, and HR—ensuring secure, context-aware data access.
  Project & Task Assignment: Intuitive interface for assigning and tracking tasks across departments and teams.
  Departmental Organization: Automatically enforces visibility rules based on employee-department relationships.
  Collaborative Workspaces: Folder-based project documentation with threaded comments to keep communication contextual and traceable.
  Secure Authentication: JWT-based authentication with email/password login (customizable via settings.py).
  Asynchronous Task Processing: Powered by Celery for background jobs (e.g., email notifications, report generation).
  Real-Time Messaging & Caching: Redis used as both Celery’s message broker and application cache layer.
  Containerized Deployment: Fully Dockerized for consistent local development and production deployment.
  Built to bridge the gap between employees and leadership, this system enhances transparency, reduces administrative overhead, and improves project tracking across complex, multi-company environments.

Tech Stack
  Backend: Python, Django, Django REST Framework
  Authentication: JWT (via djangorestframework-simplejwt)
  Frontend: React (TypeScript) (assumed based on your reference — adjust if needed)
  Database: PostgreSQL
  Task Queue: Celery
  Message Broker / Cache: Redis
  Infrastructure: Docker, Docker Compose

Quick Start (Local Development)
Fork the repository
  Click the Fork button at the top right of this GitHub page to create your own copy.
  Clone your fork 
  bash

  git clone https://github.com/your-username/project-management-system.git
  cd project-management-system
  Set up environment variables
  Create a .env file in the root directory (use .env.example as a template):
env

  DEBUG=True
  SECRET_KEY=your-secret-key
  DATABASE_URL=postgres://user:password@db:5432/pm_db
  REDIS_URL=redis://redis:6379/0
  Start with Docker Compose
  bash


1. docker-compose up --build
  The backend will run on http://localhost:8000, and the frontend on http://localhost:3000.
  Create a superuser (optional)

  docker-compose exec backend python manage.py createsuperuser
  How to Contribute
  We welcome contributions! Here’s how to get involved:

  Fork the repo (if you haven’t already).
  Create a feature branch:

  git checkout -b feature/your-feature-name
  Commit your changes:
  
  git commit -m "Add feature: your description"
  Push to your fork:

  git push origin feature/your-feature-name
  Open a Pull Request to the main branch of the original repository.
  Include a clear description of the problem and your solution.
  Reference any related issues.
  Ensure tests pass and follow existing code style.
