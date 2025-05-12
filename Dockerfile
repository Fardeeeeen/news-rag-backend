# Use official Python image
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Install system deps (if needed)
RUN apt-get update && apt-get install -y build-essential

# Copy requirements & install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
