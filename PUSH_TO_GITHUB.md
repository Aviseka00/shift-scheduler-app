# Commands to Push Code to GitHub

## After creating your GitHub repository, run these commands:

```powershell
# 1. Add all files to git
git add .

# 2. Commit the files
git commit -m "Initial commit - Shift Scheduler App ready for deployment"

# 3. Add your GitHub repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 4. Rename branch to main (if needed)
git branch -M main

# 5. Push to GitHub
git push -u origin main
```

## Important Notes:

- When you run `git push`, GitHub will ask for authentication
- You'll need to use a **Personal Access Token** (not your password)
- To create a token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
- Give it `repo` permissions
- Copy the token and use it as your password when pushing

## Example:
If your repository URL is: `https://github.com/Aviseka00/shift-scheduler-app.git`

Then run:
```powershell
git remote add origin https://github.com/Aviseka00/shift-scheduler-app.git
```

