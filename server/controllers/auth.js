const jwt = require('jsonwebtoken');

const login = async (req, res) => {
  const { username, password } = req.body || {};
  if (
    username !== process.env.ADMIN_USERNAME ||
    password !== process.env.ADMIN_PASSWORD
  ) {
    return res.status(401).json({ message: 'Invalid credentials' });
  }
  const token = jwt.sign(
    { role: 'admin', username },
    process.env.JWT_SECRET,
    { expiresIn: '12h' }
  );
  res.cookie('token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 12 * 60 * 60 * 1000,
  });
  res.status(200).json({ message: 'Login successful' });
};

const logout = async (req, res) => {
  res.clearCookie('token');
  res.status(200).json({ message: 'Logout successful' });
};

const me = async (req, res) => {
  res.status(200).json({
    username: req.admin.username,
    role: 'admin',
  });
};

module.exports = { login, logout, me };
