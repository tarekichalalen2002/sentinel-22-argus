const mongoose = require('mongoose');

const alertSchema = new mongoose.Schema(
  {
    camera: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Camera',
      required: true,
    },
    category: {
      type: String,
      enum: ['human', 'animal', 'unknown object'],
      required: true,
    },
    label: { type: String, default: '' },
    confidence: { type: Number, default: 0 },
    box: {
      x: Number,
      y: Number,
      w: Number,
      h: Number,
    },
    snapshot: { type: String },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Alert', alertSchema);
