const jwt = require('jsonwebtoken');
const Camera = require('../models/Camera');
const Notification = require('../models/Notification');
const { generateAccessKey, hashKey } = require('../utils/keys');

/** Admin: create camera → returns one-time accessKey to share with the device. */
const createCamera = async (req, res) => {
  try {
    const { name, type, location = '' } = req.body || {};
    if (!name || !['facial', 'surveillance'].includes(type)) {
      return res.status(400).json({
        message: 'name and type (facial|surveillance) are required',
      });
    }

    const accessKey = generateAccessKey(type === 'facial' ? 'FACE' : 'SURV');
    const camera = await Camera.create({
      name,
      type,
      location,
      accessKeyHash: hashKey(accessKey),
      status: 'pending',
    });

    res.status(201).json({
      message: 'Camera created — share the access key with the device',
      camera: camera.toSafeJSON(),
      accessKey,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Failed to create camera' });
  }
};

const listCameras = async (_req, res) => {
  const cameras = await Camera.find().sort({ createdAt: -1 });
  res.json({ cameras: cameras.map((c) => c.toSafeJSON()) });
};

const deleteCamera = async (req, res) => {
  const camera = await Camera.findByIdAndDelete(req.params.id);
  if (!camera) {
    return res.status(404).json({ message: 'Camera not found' });
  }
  res.json({ message: 'Camera deleted', camera: camera.toSafeJSON() });
};

const revokeCamera = async (req, res) => {
  const camera = await Camera.findByIdAndUpdate(
    req.params.id,
    { status: 'revoked' },
    { new: true }
  );
  if (!camera) {
    return res.status(404).json({ message: 'Camera not found' });
  }
  res.json({ message: 'Camera revoked', camera: camera.toSafeJSON() });
};

/**
 * Device: redeem access key → camera becomes active, returns JWT for later calls.
 * Body: { accessKey, deviceInfo? }
 */
const claimCamera = async (req, res) => {
  try {
    const { accessKey, deviceInfo = '' } = req.body || {};
    if (!accessKey) {
      return res.status(400).json({ message: 'accessKey is required' });
    }

    const camera = await Camera.findOne({
      accessKeyHash: hashKey(accessKey),
      status: 'pending',
    });
    if (!camera) {
      return res.status(401).json({ message: 'Invalid or already used access key' });
    }

    camera.status = 'active';
    camera.registeredAt = new Date();
    camera.lastSeenAt = new Date();
    camera.deviceInfo = deviceInfo;
    await camera.save();

    const token = jwt.sign(
      {
        role: 'camera',
        cameraId: camera._id.toString(),
        type: camera.type,
        name: camera.name,
      },
      process.env.JWT_SECRET,
      { expiresIn: '30d' }
    );

    await Notification.create({
      type: 'camera_registered',
      title: 'Camera registered',
      message: `${camera.name} (${camera.type}) is now active`,
      meta: { cameraId: camera._id, type: camera.type },
    });

    res.json({
      message: 'Camera registered successfully',
      token,
      camera: camera.toSafeJSON(),
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Failed to claim camera' });
  }
};

/** Device: verify saved JWT is still for an active camera. */
const cameraSession = async (req, res) => {
  res.json({ camera: req.camera.toSafeJSON() });
};

module.exports = {
  createCamera,
  listCameras,
  deleteCamera,
  revokeCamera,
  claimCamera,
  cameraSession,
};
