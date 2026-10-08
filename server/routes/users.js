const express = require('express');
const router = express.Router();
const adminAuth = require('../middleware/adminAuth');
const {
  createUser,
  listUsers,
  getUser,
  authorizeUser,
  revokeUser,
  deleteUser,
} = require('../controllers/users');

router.post('/', adminAuth, createUser);
router.get('/', adminAuth, listUsers);
router.get('/:id', adminAuth, getUser);
router.post('/:id/authorize', adminAuth, authorizeUser);
router.post('/:id/revoke', adminAuth, revokeUser);
router.delete('/:id', adminAuth, deleteUser);

module.exports = router;
