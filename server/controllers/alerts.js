const Alert = require('../models/Alert');
const Notification = require('../models/Notification');

const CATEGORIES = new Set(['human', 'animal', 'unknown object']);

/**
 * Surveillance camera: report a moving object classification.
 * Body: { category, label?, confidence?, box?, snapshot? }
 */
const createAlert = async (req, res) => {
  try {
    let { category, label = '', confidence = 0, box, snapshot } = req.body || {};
    if (category === 'unknown') category = 'unknown object';
    if (!CATEGORIES.has(category)) {
      return res.status(400).json({
        message: 'category must be human | animal | unknown object',
      });
    }

    const alert = await Alert.create({
      camera: req.camera._id,
      category,
      label,
      confidence,
      box,
      snapshot,
    });

    await Notification.create({
      type: 'motion_alert',
      title: `Motion: ${category}`,
      message: `${req.camera.name} detected ${category}${label ? ` (${label})` : ''}`,
      meta: {
        alertId: alert._id,
        cameraId: req.camera._id,
        cameraName: req.camera.name,
        category,
        label,
        confidence,
      },
    });

    res.status(201).json({
      message: 'Alert recorded',
      alert,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Failed to create alert' });
  }
};

/** Admin dashboard: recent motion alerts. */
const listAlerts = async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit, 10) || 50, 200);
  const alerts = await Alert.find()
    .sort({ createdAt: -1 })
    .limit(limit)
    .populate('camera', 'name type location status');
  res.json({ alerts });
};

/** Admin: wipe all motion alerts (and related motion_alert notifications). */
const clearAlerts = async (_req, res) => {
  const alerts = await Alert.deleteMany({});
  const notifications = await Notification.deleteMany({ type: 'motion_alert' });
  res.json({
    message: 'All alerts cleared',
    deletedAlerts: alerts.deletedCount,
    deletedNotifications: notifications.deletedCount,
  });
};

module.exports = { createAlert, listAlerts, clearAlerts };
