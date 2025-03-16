# Running MedAgent with Docker

This guide will help you run the MedAgent application using Docker, which ensures consistent setup across any computer.

## Prerequisites

1. [Docker](https://docs.docker.com/get-docker/) installed on your system
2. [Docker Compose](https://docs.docker.com/compose/install/) installed on your system

## Quick Start

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd MedAgent
   ```

2. **Important**: Make sure your `.env` file is configured correctly with your API keys:

   - OPENAI_API_KEY (required)
   - LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY (for monitoring)
   - SENDGRID_API_KEY (for email notifications)
   - ELEVEN_LABS_API_KEY (if you're using Eleven Labs for TTS)

3. Build and start the containers:

   ```bash
   docker-compose up -d
   ```

4. Access the application:

   - Web interface: http://localhost:5001

5. To stop the application:
   ```bash
   docker-compose down
   ```

## Architecture

The Docker setup includes:

- **app**: The MedAgent Flask application
- **mongo**: MongoDB database for storing appointments, doctors, and patients

## Persistent Data

MongoDB data is stored in a Docker volume (`mongo_data`), so your data will persist even after stopping and restarting the containers.

## Logs

To view the logs:

```bash
# For all services
docker-compose logs

# For a specific service (app or mongo)
docker-compose logs app
docker-compose logs mongo

# Follow logs in real-time
docker-compose logs -f
```

## Environment Variables

You can customize the application by modifying environment variables in the `.env` file or directly in the `docker-compose.yml` file.

## Troubleshooting

### MongoDB Connection Issues

If the app can't connect to MongoDB, ensure:

1. The MongoDB container is running: `docker-compose ps`
2. The MONGODB_URI is correctly set to `mongodb://mongo:27017/medagent_db` in the environment

### API Key Issues

If you see errors related to OpenAI or other external services:

1. Check that your API keys are correctly set in the `.env` file
2. Restart the containers after updating the `.env` file:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Container Build Issues

If you need to rebuild the containers:

```bash
docker-compose build --no-cache
docker-compose up -d
```
