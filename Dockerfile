FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the image
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the working directory contents into the image
COPY . .

# Expose port 8000 for the FastAPI app
EXPOSE 8000

# Command to run the FastAPI app with uvicorn
CMD ["uvicorn", "api.v1.assistent:app", "--host", "0.0.0.0", "--port", "8000"]