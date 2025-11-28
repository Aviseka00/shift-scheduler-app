# 📅 Shift & Task Scheduler Application

A modern, full-featured shift scheduling and task management system built with Flask and MongoDB.

## ✨ Features

### For Managers
- 📊 Dashboard with team overview
- 📅 Visual calendar for shift management
- 👥 Project-based team management
- 🔄 Handle shift change and swap requests
- 📤 Export shifts to CSV/Print
- ➕ Create and manage projects
- ⏰ Auto-assign shift timings (A/B/C/G shifts)

### For Members
- 📅 Personal shift calendar
- 👀 View team schedules (project-wise)
- 🔄 Request shift changes
- 🔀 Request shift swaps
- 📋 View assigned tasks

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MongoDB (local or Atlas)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/shift-scheduler-app.git
   cd shift-scheduler-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```env
   SECRET_KEY=your-secret-key-here
   MONGO_URI=mongodb://localhost:27017/shift_scheduler_db
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the app**
   - Open browser: http://127.0.0.1:5000
   - Register a manager account (use secret key: `ADMIN2025`)
   - Register member accounts

## 📦 Project Structure

```
shift_scheduler_app/
├── app.py                 # Main application file
├── config.py              # Configuration
├── extensions.py          # Flask extensions
├── requirements.txt       # Python dependencies
├── Procfile              # For deployment
├── runtime.txt           # Python version
├── auth/                 # Authentication routes
├── manager/              # Manager routes
├── member/               # Member routes
├── project/              # Project routes
├── templates/            # HTML templates
└── static/               # CSS, images
```

## 🔐 Default Manager Key

For registration, use: `ADMIN2025`

## 🌐 Deployment

### Deploy to Render

1. Push to GitHub
2. Connect to Render
3. Set environment variables:
   - `SECRET_KEY`
   - `MONGO_URI`
4. Deploy!

See `QUICK_DEPLOY.md` for detailed instructions.

## 🛠️ Technologies

- **Backend**: Flask 3.0
- **Database**: MongoDB (PyMongo)
- **Frontend**: Bootstrap 5, FullCalendar.js
- **Deployment**: Gunicorn, Render

## 📝 License

This project is open source and available for use.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues or questions, please open an issue on GitHub.

---

**Made with ❤️ for efficient shift management**

