# Deployment Guide

## Environment Variables Required

Create a `.env` file in the project root with:

```
MONGO_URI="mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/shift_scheduler_db?retryWrites=true&w=majority"
SECRET_KEY="your-random-secret-key-here"
```

## Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create `.env` file with your MongoDB Atlas connection string

3. Run the app:
   ```bash
   python app.py
   ```

## Deploy to Render (Free)

1. Push your code to GitHub
2. Go to [Render.com](https://render.com) and create a new Web Service
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3
5. Add Environment Variables in Render dashboard:
   - `MONGO_URI` - Your MongoDB Atlas connection string
   - `SECRET_KEY` - A random secret key
6. Deploy!

Your app will be available at `https://your-app-name.onrender.com`

## Notes

- The `.env` file is in `.gitignore` to protect your secrets
- Make sure MongoDB Atlas Network Access allows connections from `0.0.0.0/0` (or your Render IP)
- Manager secret key is currently hardcoded in `auth/routes.py` - consider moving to env var for production

