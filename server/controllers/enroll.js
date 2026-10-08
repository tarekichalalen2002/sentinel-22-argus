const User = require('../models/User');
const Notification = require('../models/Notification');
const { hashKey } = require('../utils/keys');

/**
 * Facial camera: complete enrollment with the user's enroll key + face data.
 * Body: { enrollKey, faceImage?, embedding? }
 */
const enrollWithKey = async (req, res) => {
  try {
    const { enrollKey, faceImage, embedding } = req.body || {};
    if (!enrollKey) {
      return res.status(400).json({ message: 'enrollKey is required' });
    }
    if (!faceImage && !(Array.isArray(embedding) && embedding.length)) {
      return res.status(400).json({
        message: 'faceImage and/or embedding is required',
      });
    }

    const user = await User.findOne({
      enrollKeyHash: hashKey(enrollKey),
      status: 'pending',
    });
    if (!user) {
      return res.status(401).json({ message: 'Invalid or already used enroll key' });
    }

    if (faceImage) user.faceImage = faceImage;
    if (Array.isArray(embedding) && embedding.length) {
      user.embedding = embedding;
    }
    user.status = 'enrolled';
    user.enrolledAt = new Date();
    user.enrolledViaCamera = req.camera._id;
    await user.save();
    await User.updateOne({ _id: user._id }, { $unset: { enrollKeyHash: 1 } });

    await Notification.create({
      type: 'user_enrolled',
      title: 'User enrolled',
      message: `${user.username} enrolled via camera "${req.camera.name}" — awaiting authorization`,
      meta: {
        userId: user._id,
        username: user.username,
        cameraId: req.camera._id,
      },
    });

    res.json({
      message: 'Enrollment successful — waiting for admin authorization',
      user: user.toSafeJSON(),
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Enrollment failed' });
  }
};

/** Facial camera: check if a recognized identity is authorized. */
const verifyAccess = async (req, res) => {
  try {
    const { username } = req.body || {};
    if (!username) {
      return res.status(400).json({ message: 'username is required' });
    }
    const user = await User.findOne({ username });
    if (!user || user.status !== 'authorized') {
      return res.json({ access: 'unauthorized', user: user ? user.toSafeJSON() : null });
    }
    res.json({ access: 'authorized', user: user.toSafeJSON() });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Verify failed' });
  }
};

/**
 * Facial camera: gallery for local matching.
 * Includes enrolled + authorized users who have face data so the camera can
 * recognize people; access is still gated on status === 'authorized'.
 */
const authorizedGallery = async (_req, res) => {
  const users = await User.find({
    status: { $in: ['enrolled', 'authorized'] },
  }).select('username fullName embedding faceImage status');

  res.json({
    users: users.map((u) => ({
      id: u._id,
      username: u.username,
      fullName: u.fullName,
      embedding: u.embedding,
      faceImage: u.faceImage,
      status: u.status,
    })),
  });
};

module.exports = { enrollWithKey, verifyAccess, authorizedGallery };
