# Step-by-Step Deployment Guide to Free Domain

## Prerequisites
- GitHub account (free) - https://github.com
- Render account (free) - https://render.com
- Freenom account (free domain) - https://www.freenom.com

---

## STEP 1: Push Code to GitHub

### 1.1 Create GitHub Repository
1. Go to https://github.com and sign in
2. Click the **"+"** icon → **"New repository"**
3. Repository name: `shift-scheduler-app` (or any name you like)
4. Description: "Shift Scheduler Application"
5. Choose **Public** (free hosting requires public repo)
6. **DO NOT** check "Initialize with README"
7. Click **"Create repository"**

### 1.2 Push Your Code
Run these commands in your terminal (in the project folder):

```powershell
# Add all files
git add .

# Commit
git commit -m "Initial commit - Ready for deployment"

# Add your GitHub repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/shift-scheduler-app.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Note:** You'll be asked for your GitHub username and password (use a Personal Access Token, not your password)

---

## STEP 2: Deploy to Render (Free Hosting)

### 2.1 Create Render Account
1. Go to https://render.com
2. Click **"Get Started for Free"**
3. Sign up with your GitHub account (recommended) or email

### 2.2 Create Web Service
1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Click **"Connect account"** if not already connected to GitHub
3. Find and select your repository: `shift-scheduler-app`
4. Click **"Connect"**

### 2.3 Configure Service
Fill in these settings:

- **Name:** `shift-scheduler-app` (or any name)
- **Region:** Choose closest to you (e.g., Singapore, US East)
- **Branch:** `main`
- **Root Directory:** (leave empty)
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Plan:** **Free** (select this)

### 2.4 Add Environment Variables
Click **"Advanced"** → **"Add Environment Variable"** and add:

1. **MONGO_URI**
   - Value: `mongodb+srv://rorosapiroteam_db_user:Arjun%401234%2E@cluster0.syq2mmr.mongodb.net/shift_scheduler_db?retryWrites=true&w=majority`

2. **SECRET_KEY**
   - Value: `your-random-secret-key-here` (generate a long random string)

3. Click **"Create Web Service"**

### 2.5 Wait for Deployment
- Render will build and deploy your app (takes 5-10 minutes)
- You'll see build logs in real-time
- When done, you'll get a URL like: `https://shift-scheduler-app.onrender.com`

**✅ Your app is now live!** Test it at the Render URL.

---

## STEP 3: Get Free Domain (Optional but Recommended)

### 3.1 Register Free Domain at Freenom
1. Go to https://www.freenom.com
2. Sign up for a free account
3. Search for a free domain (e.g., `yoursite.tk`, `yoursite.ml`, `yoursite.ga`)
4. Add to cart and complete checkout (it's free!)

### 3.2 Connect Domain to Render
1. In Render dashboard, go to your service
2. Click **"Settings"** tab
3. Scroll to **"Custom Domains"**
4. Click **"Add"**
5. Enter your domain: `yoursite.tk` (or whatever you registered)
6. Render will show you DNS settings

### 3.3 Configure DNS at Freenom
1. Go to Freenom → **"My Domains"** → **"Manage Domain"**
2. Click **"Manage Freenom DNS"**
3. Add a **CNAME record**:
   - **Name:** `www` (or `@` for root domain)
   - **Type:** `CNAME`
   - **Target:** `shift-scheduler-app.onrender.com` (your Render URL)
   - **TTL:** `3600`
4. Save changes

### 3.4 Wait for DNS Propagation
- DNS changes take 5 minutes to 48 hours
- Check status in Render dashboard
- When active, your domain will work!

---

## STEP 4: Verify Everything Works

1. **Test Render URL:** `https://your-app.onrender.com`
2. **Test Custom Domain:** `https://yoursite.tk` (after DNS propagates)
3. **Register a new user** - should save to MongoDB Atlas
4. **Login** - should work correctly
5. **Check MongoDB Atlas** - verify data is being saved

---

## Troubleshooting

### App won't start?
- Check Render logs for errors
- Verify environment variables are set correctly
- Make sure MONGO_URI has encoded password

### Domain not working?
- Wait 24-48 hours for DNS propagation
- Check DNS settings match Render's requirements
- Verify CNAME record is correct

### Database connection issues?
- Check MongoDB Atlas Network Access allows `0.0.0.0/0`
- Verify MONGO_URI is correct in Render environment variables

---

## Important Notes

⚠️ **Free Tier Limitations:**
- Render free tier spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds to wake up
- Free domains from Freenom require renewal every year

✅ **Your app is production-ready!**

Need help with any step? Let me know!

