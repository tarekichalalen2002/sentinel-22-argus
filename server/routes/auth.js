const express = require('express');
const router = express.Router();
const { login, logout, me } = require('../controllers/auth');
const adminAuth = require('../middleware/adminAuth');

router.post('/login', login);
router.post('/logout', adminAuth, logout);
router.get('/me', adminAuth, me);

module.exports = router;
