# 🩺 THUNAI

> Your family's companion for taking medicines on time.

Missed medicines are a serious problem, especially for elderly people living
alone. **THUNAI** (துணை, "companion") helps people stay on schedule and makes
sure their family is alerted when a dose is missed.

## ✨ Features

- 🔐 Secure authentication with JWT
- 💊 Medicine scheduling with repeat reminders
- ✅ Daily dashboard: taken / pending / missed at a glance
- 🚨 Automatic family alerts if a dose isn't confirmed in time
- 📊 Weekly adherence reports
- 🤖 AI health coach for daily tips
- 🆘 One-tap SOS for emergencies
- 👵 Elder-friendly mode (large text, high contrast)

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), Tailwind CSS, React Router, Context API |
| Backend | Python, Flask, PyMongo, JWT |
| Database | MongoDB |
| AI | Gemini API |

## 🚀 Getting Started

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## 🗺️ Roadmap

- [x] Project foundation (Flask API + React app)
- [ ] Authentication
- [ ] Medicine management
- [ ] Missed-dose detection & family alerts
- [ ] Weekly reports
- [ ] AI health coach
- [ ] Mobile app

## 💡 Vision

Web first, then mobile, so no one has to take their medicines alone.

---
Built by [Vignesh](https://github.com/vickyongit)
