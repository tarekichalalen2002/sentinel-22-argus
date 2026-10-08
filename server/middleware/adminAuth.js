const jwt = require('jsonwebtoken');

const adminAuth = (req, res, next) => {
  const token = req.cookies.token;
  if (!token) {
    return res.status(401).json({ message: 'Unauthorized' });
  }
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    if (decoded.role !== 'admin' && decoded.username !== process.env.ADMIN_USERNAME) {
      return res.status(401).json({ message: 'Unauthorized' });
    }
    req.admin = decoded;
    next();
  } catch {
    return res.status(401).json({ message: 'Unauthorized' });
  }
};

module.exports = adminAuth;
