const Notification = require('../models/Notification');

const listNotifications = async (req, res) => {
  const unreadOnly = req.query.unread === '1' || req.query.unread === 'true';
  const limit = Math.min(parseInt(req.query.limit, 10) || 50, 200);
  const filter = unreadOnly ? { read: false } : {};
  const notifications = await Notification.find(filter)
    .sort({ createdAt: -1 })
    .limit(limit);
  const unreadCount = await Notification.countDocuments({ read: false });
  res.json({ notifications, unreadCount });
};

const markRead = async (req, res) => {
  const notification = await Notification.findByIdAndUpdate(
    req.params.id,
    { read: true },
    { new: true }
  );
  if (!notification) {
    return res.status(404).json({ message: 'Notification not found' });
  }
  res.json({ notification });
};

const markAllRead = async (_req, res) => {
  const result = await Notification.updateMany({ read: false }, { read: true });
  res.json({ message: 'All notifications marked read', modified: result.modifiedCount });
};

const clearNotifications = async (_req, res) => {
  const result = await Notification.deleteMany({});
  res.json({ message: 'All notifications cleared', deleted: result.deletedCount });
};

module.exports = { listNotifications, markRead, markAllRead, clearNotifications };
