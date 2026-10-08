const crypto = require('crypto');

/** Human-readable pairing / enroll key, e.g. CAM-A1B2-C3D4-E5F6-7890 */
function generateAccessKey(prefix = 'CAM') {
  const raw = crypto.randomBytes(8).toString('hex').toUpperCase();
  return `${prefix}-${raw.slice(0, 4)}-${raw.slice(4, 8)}-${raw.slice(8, 12)}-${raw.slice(12)}`;
}

/** SHA-256 hex digest for O(1) lookup of high-entropy keys. */
function hashKey(key) {
  return crypto.createHash('sha256').update(String(key).trim()).digest('hex');
}

module.exports = { generateAccessKey, hashKey };
