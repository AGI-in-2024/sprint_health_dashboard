# Sprint Health Dashboard Setup Instructions

## Clone the Repository
1. Clone the repository:
   ```
   git clone https://github.com/AGI-in-2024/sprint-health-dashboard.git
   cd sprint-health-dashboard
   ```

## Set Up Virtual Environment
2. Create and activate a virtual environment:

   ### On Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

   ### On macOS/Linux:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Start the Backend
4. Navigate to the backend directory and start the server:
   ```
   cd backend
   uvicorn main:app --reload
   ```

## Start the Frontend
5. Open a new terminal and navigate to the frontend directory:
   ```
   cd frontend
   npm install
   npm run dev
   ```
