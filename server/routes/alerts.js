const express = require('express');
const router = express.Router();
const adminAuth = require('../middleware/adminAuth');
const { cameraAuth, requireCameraType } = require('../middleware/cameraAuth');
const { createAlert, listAlerts, clearAlerts } = require('../controllers/alerts');

router.post('/', cameraAuth, requireCameraType('surveillance'), createAlert);
router.get('/', adminAuth, listAlerts);
router.delete('/', adminAuth, clearAlerts);

module.exports = router;
