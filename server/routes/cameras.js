const express = require('express');
const router = express.Router();
const adminAuth = require('../middleware/adminAuth');
const { cameraAuth } = require('../middleware/cameraAuth');
const {
  createCamera,
  listCameras,
  deleteCamera,
  revokeCamera,
  claimCamera,
  cameraSession,
} = require('../controllers/cameras');

/** Device pairing — no admin cookie; uses one-time access key. */
router.post('/claim', claimCamera);

/** Device: confirm token still belongs to an active (non-revoked) camera. */
router.get('/me', cameraAuth, cameraSession);

router.post('/', adminAuth, createCamera);
router.get('/', adminAuth, listCameras);
router.delete('/:id', adminAuth, deleteCamera);
router.post('/:id/revoke', adminAuth, revokeCamera);

module.exports = router;
