# ⚡ Quick Deploy Guide

## 🎯 Step-by-Step Instructions

### PART 1: Push to GitHub

#### Step 1: Check Git Status
```bash
git status
```

#### Step 2: Add All Files
```bash
git add .
```

#### Step 3: Commit
```bash
git commit -m "Complete Shift Scheduler App - Ready for deployment"
```

#### Step 4: Create GitHub Repository
1. Go to: https://github.com/new
2. Repository name: `shift-scheduler-app`
3. Description: "Shift and Task Scheduler Application"
4. Choose: **Public** or **Private**
5. **DO NOT** check any boxes (no README, .gitignore, license)
6. Click **"Create repository"**

#### Step 5: Connect and Push
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/shift-scheduler-app.git
git branch -M main
git push -u origin main
```

**If you get authentication error:**
- Use GitHub Personal Access Token instead of password
- Or use GitHub Desktop app

---

### PART 2: Deploy to Render

#### Step 1: Sign Up/Login
- Go to: https://render.com
- Sign up with GitHub (recommended)

#### Step 2: Create New Web Service
1. Click **"New +"** button
2. Select **"Web Service"**
3. Connect your GitHub account (if not connected)
4. Select repository: `shift-scheduler-app`
5. Click **"Connect"**

#### Step 3: Configure Service
Fill in these details:

- **Name**: `shift-scheduler-app`
- **Region**: Choose closest (e.g., `Oregon (US West)`)
- **Branch**: `main`
- **Root Directory**: (leave empty)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

#### Step 4: Add Environment Variables
Click **"Advanced"** → **"Add Environment Variable"**

Add these **3 variables**:

1. **SECRET_KEY**
   - Generate one: Run this in terminal:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - Copy the output and paste as value

2. **MONGO_URI**
   - Your MongoDB Atlas connection string
   - Format: `mongodb+srv://username:password@cluster.mongodb.net/shift_scheduler_db?retryWrites=true&w=majority`
   - Replace `username`, `password`, and `cluster` with your values

3. **PYTHON_VERSION** (optional)
   - Value: `3.11.0`

#### Step 5: Deploy
1. Click **"Create Web Service"**
2. Wait 5-10 minutes for first deployment
3. Watch the build logs
4. Once done, you'll get a URL like: `https://shift-scheduler-app.onrender.com`

---

### PART 3: Test Your Live App

1. Visit your Render URL
2. Register a new user
3. Test all features:
   - Login/Register
   - Create projects
   - Add shifts
   - View calendars
   - Request changes/swaps

---

## 🔧 Troubleshooting

### Build Fails?
- Check build logs in Render
- Verify `requirements.txt` is correct
- Check Python version

### App Won't Start?
- Check environment variables
- Verify MongoDB connection
- Check logs in Render dashboard

### Database Connection Error?
- Verify MongoDB Atlas IP whitelist: `0.0.0.0/0`
- Check MongoDB URI format
- Ensure database user exists

---

## 📝 Important Notes

✅ **Never commit these to GitHub:**
- `.env` file
- `SECRET_KEY` in code
- MongoDB credentials in code

✅ **Always set in Render:**
- `SECRET_KEY` (environment variable)
- `MONGO_URI` (environment variable)

✅ **Free Tier Limits:**
- Render free tier: App sleeps after 15 min inactivity
- First request after sleep takes ~30 seconds
- MongoDB Atlas free tier: 512MB storage

---

## 🎉 Success!

Once deployed, your app will be live at:
`https://shift-scheduler-app.onrender.com`

**Auto-deployment:** Every time you push to GitHub, Render will automatically redeploy!

---

## 📞 Need Help?

1. Check `DEPLOYMENT_GUIDE.md` for detailed instructions
2. Review Render logs
3. Check MongoDB Atlas connection
4. Verify all environment variables are set

Good luck! 🚀

