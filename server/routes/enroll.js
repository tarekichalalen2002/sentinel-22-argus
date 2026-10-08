const express = require('express');
const router = express.Router();
const { cameraAuth, requireCameraType } = require('../middleware/cameraAuth');
const {
  enrollWithKey,
  verifyAccess,
  authorizedGallery,
} = require('../controllers/enroll');

router.use(cameraAuth, requireCameraType('facial'));

router.post('/', enrollWithKey);
router.post('/verify', verifyAccess);
router.get('/gallery', authorizedGallery);

module.exports = router;
