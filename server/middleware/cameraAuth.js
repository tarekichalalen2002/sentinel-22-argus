const jwt = require('jsonwebtoken');
const Camera = require('../models/Camera');

/** Requires Authorization: Bearer <camera-jwt> from /api/cameras/claim */
const cameraAuth = async (req, res, next) => {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) {
    return res.status(401).json({ message: 'Camera token required' });
  }
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    if (decoded.role !== 'camera' || !decoded.cameraId) {
      return res.status(401).json({ message: 'Invalid camera token' });
    }
    const camera = await Camera.findById(decoded.cameraId);
    if (!camera || camera.status !== 'active') {
      return res.status(401).json({ message: 'Camera not active' });
    }
    camera.lastSeenAt = new Date();
    await camera.save();
    req.camera = camera;
    next();
  } catch {
    return res.status(401).json({ message: 'Invalid camera token' });
  }
};

/** Restrict to a camera type after cameraAuth */
const requireCameraType = (...types) => (req, res, next) => {
  if (!req.camera || !types.includes(req.camera.type)) {
    return res.status(403).json({
      message: `This endpoint requires a ${types.join(' or ')} camera`,
    });
  }
  next();
};

module.exports = { cameraAuth, requireCameraType };
