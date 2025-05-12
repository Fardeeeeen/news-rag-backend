# news-rag-backend

The News Chatbot is a Retrieval-Augmented Generation (RAG) application that delivers real-time news updates in response to user queries. It crawls news articles from RSS feeds, processes and indexes them using ChromaDB, and generates conversational responses using Google’s Gemini LLM. The backend is built with FastAPI, and the system uses Redis for session management. The frontend (assumed to be a web interface) provides a user-friendly chat interface for interacting with the bot.
Features

News Crawling: Fetches articles from RSS feeds using feedparser and NewsPlease.
Text Processing: Splits articles into passages (~150 words) for efficient retrieval.
Vector Search: Indexes passages in ChromaDB with all-MiniLM-L6-v2 embeddings for semantic search.
Conversational AI: Uses Google Gemini (gemini-1.5-flash) to generate context-aware responses.
Session Management: Stores chat history in Redis for persistent conversations.
REST API: FastAPI backend with endpoints for chat, session deletion, and debugging.
Containerized Deployment: Dockerized setup with Docker Compose for easy deployment.

Tech Stack

Backend: Python 3.10, FastAPI, Uvicorn
News Crawling: feedparser, NewsPlease
Vector Database: ChromaDB with all-MiniLM-L6-v2 embeddings
LLM: Google Gemini (gemini-1.5-flash)
Session Storage: Redis
Frontend: [Assumed: React, HTML/CSS/JavaScript]
Containerization: Docker, Docker Compose
Dependencies: See requirements.txt and package.json

Prerequisites

Python 3.10+
Docker and Docker Compose
Google API key for Gemini (GOOGLE_API_KEY)
Node.js (if frontend is included)
Redis server (included in Docker Compose)
RSS feed URLs in backend/data/raw/news_rss.txt

Installation
1. Clone the Repository
git clone https://github.com/your-username/news-chatbot.git
cd news-chatbot

2. Set Up Environment Variables
Create a .env file in the root directory with the following:
GOOGLE_API_KEY=your_google_api_key
REDIS_URL=redis://redis:6379/0

3. Build and Run with Docker Compose
docker-compose up --build

This starts:

The FastAPI backend on http://localhost:8000
A Redis instance on port 6379

4. (Optional) Run Backend Locally
If you prefer to run the backend without Docker:
cd backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000

5. (Optional) Set Up Frontend
[If you share the frontend code, I can add specific instructions. For now, assuming a React frontend:]
cd frontend
npm install
npm start

Open http://localhost:3000 to access the chat interface.
6. Prepare News Data
To crawl and index news articles:

Ensure RSS feed URLs are listed in backend/data/raw/news_rss.txt.
Run the crawler:python backend/embed/crawl_with_newsplease.py


Process articles into passages:python backend/ingest/split_passages.py


Index passages in ChromaDB:python backend/ingest/embed_and_index_chroma.py



Usage

Access the frontend (e.g., http://localhost:3000) or interact with the API directly.
Send a POST request to /chat with a JSON payload:{
    "session_id": "unique_session_id",
    "message": "What's the latest tech news?"
}


The bot retrieves relevant passages from ChromaDB, combines them with chat history, and generates a response using Gemini.
Clear a session by sending a DELETE request to /session/{session_id}.
Use the /debug_raw endpoint for raw Gemini response debugging.

API Endpoints

POST /chat: Send a user message and receive a response.
Request: { "session_id": str, "message": str }
Response: { "response": str, "session_history": [{ "user": str, "bot": str }] }


DELETE /session/{session_id}: Clear a session’s chat history.
POST /debug_raw: Debug raw Gemini responses for a given message.

Project Structure
news-chatbot/
├── backend/
│   ├── data/
│   │   ├── raw/
│   │   │   ├── news_rss.txt        # RSS feed URLs
│   │   │   └── news_full.json      # Crawled articles
│   │   └── processed/
│   │       ├── passages.jsonl      # Processed passages
│   │       └── chroma_db/          # ChromaDB storage
│   ├── embed/
│   │   └── crawl_with_newsplease.py # Crawls RSS feeds
│   ├── ingest/
│   │   ├── embed_and_index_chroma.py # Indexes passages
│   │   └── split_passages.py        # Splits articles
│   ├── node_modules/                # CORS middleware
│   ├── app.py                       # FastAPI backend
│   ├── requirements.txt             # Python dependencies
│   └── package.json                 # Node.js dependencies
├── Dockerfile                       # Backend container
├── docker-compose.yml               # Service configuration
├── package.json                     # Project metadata
└── README.md                        # Project documentation

Contributing

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit changes (git commit -m 'Add your feature').
Push to the branch (git push origin feature/your-feature).
Open a pull request.

License
This project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgements

NewsPlease for article crawling.
ChromaDB for vector storage.
Google Gemini for conversational AI.
FastAPI for the API framework.
Redis for session management.

