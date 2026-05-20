# IPL Analytics Dashboard 🏏

An end-to-end, production-ready full-stack analytics engine built for exploring cricket match datasets. It provides rich visualizations, fast analytical querying, and a robust data ingestion pipeline capable of handling malformed or "dirty" data seamlessly.

## 🌟 Features
- **Robust Data Pipeline**: Ingests JSON files, gracefully skipping malformed data using error handling strategies, ensuring no application crashes.
- **FastAPI Backend**: Uses Pandas and SQLite to aggregate and serve fast analytics on demand.
- **Glassmorphism UI**: A premium, visually stunning React frontend powered by Recharts, offering dark mode aesthetics with seamless animations and responsiveness.
- **Interactive Analytics**: Drill-down on stats, win rates, toss impacts, top players, and venue performance based on specific seasons.

## 🛠 Tech Stack
- **Backend**: Python 3.12, FastAPI, Pandas, SQLite
- **Frontend**: React, Vite, Recharts, Lucide React
- **Architecture**: In-memory/SQLite persistence for rapid access, decoupled API & frontend.

## 🛡️ Fault Tolerance & Dirty Data Handling
To ensure the analytics engine never crashes during ingestion and prevents silent data corruption, the pipeline employs strict defensive programming:
1. **Row-Level Error Boundary (`try-except`)**: Instead of wrapping whole files, individual ball-by-ball deliveries are wrapped in exception blocks. If a single faulty row is encountered (e.g., malformed player names or missing objects), the specific error is logged and only that row is skipped, retaining the rest of the perfectly valid match data.
2. **Safe Dictionary Retrieval**: Using Python's `.get('key', default)` method guarantees that completely missing records (e.g. an abandoned match without a winner) gracefully fall back to values like `"Unknown"` instead of throwing fatal `KeyError` exceptions.
3. **Explicit Type Verification**: Nested dictionaries are type-checked before parsing (`if not isinstance(runs, dict)`) to thwart `AttributeError` crashes in case corrupted JSON arrays appear where dictionaries are expected.
4. **File-Level Validation**: Entirely broken JSON files are caught via `json.JSONDecodeError` at load time and immediately bypassed, ensuring the ingestion server continues running uninterrupted.

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Data Placement
1. Download the IPL/Cricsheet JSON dataset.
2. Create a folder named `data` in the root of this project (or place it wherever you prefer).
3. Extract all `.json` match files into that folder.

### 1. Backend Setup
Navigate to the root directory and set up the Python environment:
```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn pandas sqlalchemy

# Run the backend (it will automatically parse the dataset and create the SQLite DB)
cd backend
export DATA_DIR="../data" # Set this to the absolute path if stored elsewhere
uvicorn main:app --reload --port 8000
```
*The API will be available at http://localhost:8000. You can view the API documentation at http://localhost:8000/docs.*

### 2. Frontend Setup
In a new terminal window, start the React application:
```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
*The app will be available at http://localhost:5173.*

## 📜 License
This project is open-sourced under the MIT License. See `LICENSE` for more details.
