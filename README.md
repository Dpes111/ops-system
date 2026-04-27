# OpsSystem v2 — Python + HTML/CSS/JS

## Structure
```
ops-system-v2/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── supabase_client.py
│   └── routers/
│       ├── auth.py
│       ├── tasks.py
│       ├── attendance.py
│       └── notifications.py
└── frontend/
    ├── index.html        ← Login
    ├── dashboard.html
    ├── tasks.html
    ├── checkin.html
    ├── chat.html
    ├── users.html
    ├── staff.html
    ├── logs.html
    ├── map.html
    ├── sw.js             ← Service Worker
    ├── manifest.json     ← PWA
    ├── css/app.css
    └── js/
        ├── config.js     ← ⚠️ Update your keys here
        ├── api.js
        └── layout.js
```

## Step 1 — Update config.js
Edit `frontend/js/config.js`:
```js
window.API_URL         = 'https://YOUR-BACKEND.onrender.com/api';
window.SUPABASE_URL    = 'https://jmbczkhjrewsqqfdhiry.supabase.co';
window.SUPABASE_ANON_KEY = 'YOUR_ANON_KEY';
```

## Step 2 — Deploy Backend on Render
- New Web Service → connect repo
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add env variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, etc.)

## Step 3 — Deploy Frontend on Render
- New Static Site → connect repo
- Root Directory: `frontend`
- Build Command: (leave empty)
- Publish Directory: `frontend`

## Step 4 — Add PWA Icons
Put these files in `frontend/icons/`:
- icon-192.png
- icon-512.png
- badge-72.png
(Already created as placeholders)

## Step 5 — Create Admin User
In Supabase SQL Editor:
```sql
-- After creating user in Auth dashboard:
INSERT INTO profiles (id, full_name, email, role, is_active)
SELECT id, 'Your Name', email, 'admin'::user_role, true
FROM auth.users WHERE email = 'your@email.com'
ON CONFLICT (id) DO UPDATE SET role = 'admin'::user_role, is_active = true;
```
