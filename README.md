# Travel Recommendation System

This project implements a travel recommendation system for Bangladesh districts using Django. It fetches weather and air quality data from the Open-Meteo API to rank the top 10 coolest and cleanest districts and provides travel recommendations based on user input.

## Features
- **Top 10 Coolest & Cleanest Districts**: Ranks districts based on average temperature and PM2.5 levels over a 7-day forecast.
- **Travel Recommendation**: Compares temperature and air quality between a user's current district and destination district on a specified travel date.
- **Tabbed UI**: A user-friendly interface with tabs for "Top Districts" and "Travel Recommendation".

## Requirements
- Python 3.10+
- Django 4.2.16
- Django REST Framework 3.15.2
- Requests 2.32.3
- aiohttp 3.10.10 (for asynchronous API requests)
- SQLite (default database)

## Installation
Follow these steps to set up and run the project locally:

## 1. Clone the Repository:
   ```bash
   git clone https://github.com/yourusername/travel-recommendation-system.git
   cd travel-recommendation-system
   ```

## 2. Create a Virtual Environment

This isolates the project’s dependencies from your system Python.

```bash
python -m venv venv
```

## 3. Activate the Virtual Environment

### On Windows:

```bash
venv\Scripts\activate
```

### On macOS/Linux:

```bash
source venv/bin/activate
```

> After activation, your terminal prompt should show `(venv)`.

## 4. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 5. Run Migrations

Set up the database and create necessary tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 6. Run the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

Open your browser and go to [http://127.0.0.1:8000](http://127.0.0.1:8000) to access the Travel Recommendation System.

---

## Additional Notes

- Ensure you have a stable internet connection for fetching weather and air quality data from the **Open-Meteo API**.
- If needed, create a superuser for accessing the Django admin panel:

```bash
python manage.py createsuperuser
```

---

## License

This project is licensed under the **MIT License**.
