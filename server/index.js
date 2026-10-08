const path = require('path');
const fs = require('fs');
const express = require('express');
const mongoose = require('mongoose');
const dotenv = require('dotenv');
const cookieParser = require('cookie-parser');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

dotenv.config({ path: path.resolve(__dirname, '.env') });

const authRoutes = require('./routes/auth');
const cameraRoutes = require('./routes/cameras');
const userRoutes = require('./routes/users');
const enrollRoutes = require('./routes/enroll');
const alertRoutes = require('./routes/alerts');
const notificationRoutes = require('./routes/notifications');

const app = express();
const port = Number(process.env.PORT) || 3000;
const staticDir = path.join(__dirname, 'static');
const clientOrigin = process.env.CLIENT_ORIGIN || 'http://localhost:5173';

if (!process.env.MONGO_URI) {
  console.error('MONGO_URI is missing — check server/.env');
  process.exit(1);
}
if (!process.env.JWT_SECRET) {
  console.error('JWT_SECRET is missing — check server/.env');
  process.exit(1);
}

app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
        fontSrc: ["'self'", 'https://fonts.gstatic.com', 'data:'],
        imgSrc: ["'self'", 'data:', 'blob:'],
        connectSrc: ["'self'", clientOrigin],
        objectSrc: ["'none'"],
        frameAncestors: ["'none'"],
      },
    },
  })
);

app.use(
  cors({
    origin: [clientOrigin, `http://localhost:${port}`, `http://127.0.0.1:${port}`],
    credentials: true,
  })
);
app.use(express.json({ limit: '10mb' }));
app.use(morgan('dev'));
app.use(cookieParser());

app.get('/api/health', (_req, res) => {
  res.json({ ok: true });
});

app.use('/api/auth', authRoutes);
app.use('/api/cameras', cameraRoutes);
app.use('/api/users', userRoutes);
app.use('/api/enroll', enrollRoutes);
app.use('/api/alerts', alertRoutes);
app.use('/api/notifications', notificationRoutes);

app.use(express.static(staticDir, { index: false }));

app.use((req, res, next) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') return next();
  if (req.path.startsWith('/api')) return next();
  const indexHtml = path.join(staticDir, 'index.html');
  if (!fs.existsSync(indexHtml)) {
    return res
      .status(503)
      .type('text')
      .send('Dashboard not built. Run: npm run build:ui (from server/)');
  }
  res.sendFile(indexHtml);
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ message: 'Internal server error' });
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
  if (fs.existsSync(path.join(staticDir, 'index.html'))) {
    console.log(`Dashboard: http://localhost:${port}`);
  } else {
    console.log('Dashboard missing — run: npm run build:ui');
  }
  mongoose
    .connect(process.env.MONGO_URI)
    .then(() => console.log('Connected to MongoDB'))
    .catch((err) => console.error('Failed to connect to MongoDB', err));
});
