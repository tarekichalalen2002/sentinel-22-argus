const User = require('../models/User');
const Notification = require('../models/Notification');
const { generateAccessKey, hashKey } = require('../utils/keys');

/** Admin: create pending user + one-time enroll key to send to the person. */
const createUser = async (req, res) => {
  try {
    const { username, email, fullName = '' } = req.body || {};
    if (!username || !email) {
      return res.status(400).json({ message: 'username and email are required' });
    }

    const enrollKey = generateAccessKey('ENRL');
    const user = await User.create({
      username,
      email,
      fullName,
      enrollKeyHash: hashKey(enrollKey),
      status: 'pending',
    });

    res.status(201).json({
      message: 'User created — send them the enroll key for the facial camera',
      user: user.toSafeJSON(),
      enrollKey,
    });
  } catch (err) {
    if (err.code === 11000) {
      return res.status(409).json({ message: 'Username or email already exists' });
    }
    console.error(err);
    res.status(500).json({ message: 'Failed to create user' });
  }
};

const listUsers = async (_req, res) => {
  const users = await User.find().sort({ createdAt: -1 });
  res.json({ users: users.map((u) => u.toSafeJSON()) });
};

const getUser = async (req, res) => {
  const user = await User.findById(req.params.id);
  if (!user) {
    return res.status(404).json({ message: 'User not found' });
  }
  res.json({ user: user.toSafeJSON() });
};

/** Admin: mark enrolled user as authorized → dashboard notification. */
const authorizeUser = async (req, res) => {
  try {
    const user = await User.findById(req.params.id);
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }
    if (user.status !== 'enrolled' && user.status !== 'authorized') {
      return res.status(400).json({
        message: 'User must be enrolled at a facial camera before authorization',
      });
    }

    user.status = 'authorized';
    user.authorizedAt = new Date();
    await user.save();

    await Notification.create({
      type: 'user_authorized',
      title: 'User authorized',
      message: `${user.username} is now authorized`,
      meta: { userId: user._id, username: user.username },
    });

    res.json({
      message: 'User authorized',
      user: user.toSafeJSON(),
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Failed to authorize user' });
  }
};

const revokeUser = async (req, res) => {
  const user = await User.findByIdAndUpdate(
    req.params.id,
    { status: 'revoked' },
    { new: true }
  );
  if (!user) {
    return res.status(404).json({ message: 'User not found' });
  }
  res.json({ message: 'User revoked', user: user.toSafeJSON() });
};

const deleteUser = async (req, res) => {
  const user = await User.findByIdAndDelete(req.params.id);
  if (!user) {
    return res.status(404).json({ message: 'User not found' });
  }
  res.json({ message: 'User deleted', user: user.toSafeJSON() });
};

module.exports = {
  createUser,
  listUsers,
  getUser,
  authorizeUser,
  revokeUser,
  deleteUser,
};
