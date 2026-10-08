const express = require('express');
const router = express.Router();
const adminAuth = require('../middleware/adminAuth');
const {
  listNotifications,
  markRead,
  markAllRead,
  clearNotifications,
} = require('../controllers/notifications');

router.get('/', adminAuth, listNotifications);
router.post('/read-all', adminAuth, markAllRead);
router.delete('/', adminAuth, clearNotifications);
router.post('/:id/read', adminAuth, markRead);

module.exports = router;
