const mongoose = require('mongoose');

const userSchema = new mongoose.Schema(
  {
    username: { type: String, required: true, unique: true, trim: true },
    email: { type: String, required: true, unique: true, trim: true, lowercase: true },
    fullName: { type: String, default: '', trim: true },
    /** SHA-256 of one-time enroll key (plaintext only returned on create). */
    enrollKeyHash: { type: String, unique: true, sparse: true },
    status: {
      type: String,
      enum: ['pending', 'enrolled', 'authorized', 'revoked'],
      default: 'pending',
    },
    embedding: { type: [Number], default: undefined },
    faceImage: { type: String, default: undefined },
    enrolledAt: { type: Date },
    authorizedAt: { type: Date },
    enrolledViaCamera: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Camera',
      default: null,
    },
  },
  { timestamps: true }
);

userSchema.methods.toSafeJSON = function toSafeJSON() {
  return {
    id: this._id,
    username: this.username,
    email: this.email,
    fullName: this.fullName,
    status: this.status,
    hasFace: Boolean(this.faceImage || (this.embedding && this.embedding.length)),
    enrolledAt: this.enrolledAt,
    authorizedAt: this.authorizedAt,
    enrolledViaCamera: this.enrolledViaCamera,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt,
  };
};

module.exports = mongoose.model('User', userSchema);
