const mongoose = require('mongoose');

const cameraSchema = new mongoose.Schema(
  {
    name: { type: String, required: true, trim: true },
    type: {
      type: String,
      enum: ['facial', 'surveillance'],
      required: true,
    },
    location: { type: String, default: '' },
    /** SHA-256 of the one-time access key (plaintext only returned on create). */
    accessKeyHash: { type: String, required: true, unique: true },
    status: {
      type: String,
      enum: ['pending', 'active', 'revoked'],
      default: 'pending',
    },
    registeredAt: { type: Date },
    lastSeenAt: { type: Date },
    deviceInfo: { type: String, default: '' },
  },
  { timestamps: true }
);

cameraSchema.methods.toSafeJSON = function toSafeJSON() {
  return {
    id: this._id,
    name: this.name,
    type: this.type,
    location: this.location,
    status: this.status,
    registeredAt: this.registeredAt,
    lastSeenAt: this.lastSeenAt,
    deviceInfo: this.deviceInfo,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt,
  };
};

module.exports = mongoose.model('Camera', cameraSchema);
