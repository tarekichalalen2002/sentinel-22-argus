const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
    username: { type: String, required: true, unique: true },
    password: { type: String, required: true },
    email: { type: String, required: true, unique: true },
    createdAt: { type: Date, default: Date.now },
    embedding: { type: [Number], required: true },
    faceImage: { type: String, required: true },
});

const User = mongoose.model('User', userSchema);

module.exports = User;