# Fix MongoDB Atlas Connection Issues on Render

## Problem
SSL handshake failures when connecting to MongoDB Atlas from Render.

## Solution Steps

### Step 1: Check MongoDB Atlas Network Access

1. Go to **MongoDB Atlas Dashboard**: https://cloud.mongodb.com
2. Click on your cluster
3. Go to **"Network Access"** (left sidebar)
4. Click **"Add IP Address"**
5. Click **"Allow Access from Anywhere"** (adds `0.0.0.0/0`)
   - OR add Render's IP ranges if you want more security
6. Click **"Confirm"**

**This is the most common cause of connection failures!**

### Step 2: Verify Database User

1. Go to **"Database Access"** (left sidebar)
2. Make sure your user `rorosapiroteam_db_user` exists
3. User should have **"Read and write to any database"** permission
4. If password was changed, update it in Render environment variables

### Step 3: Update Connection String in Render

1. Go to your Render dashboard
2. Select your service
3. Go to **"Environment"** tab
4. Find `MONGO_URI` variable
5. Update it to this format (with proper encoding):

```
mongodb+srv://rorosapiroteam_db_user:Arjun%401234%2E@cluster0.syq2mmr.mongodb.net/shift_scheduler_db?retryWrites=true&w=majority&tls=true
```

**Important:** The password `Arjun@1234.` must be URL-encoded as `Arjun%401234%2E`

### Step 4: Redeploy

After updating environment variables:
1. Go to **"Manual Deploy"** → **"Deploy latest commit"**
2. Wait for deployment to complete
3. Check logs for any errors

## Alternative: Use Connection String from Atlas

1. In MongoDB Atlas, click **"Connect"** on your cluster
2. Choose **"Connect your application"**
3. Select **"Python"** and version **"3.6 or later"**
4. Copy the connection string
5. Replace `<password>` with your actual password (URL-encoded)
6. Update `MONGO_URI` in Render with this string

## Test Connection

After fixing, test by:
1. Visiting your Render app URL
2. Try to register a new user
3. Check MongoDB Atlas → Collections to see if data appears

If still failing, check Render logs for specific error messages.

