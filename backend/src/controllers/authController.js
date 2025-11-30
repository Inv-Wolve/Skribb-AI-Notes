const bcrypt = require('bcrypt');
const User = require('../models/User');
const { createSession, deleteSession, getSession } = require('../middleware/auth');
const { SALT_ROUNDS, IS_DEVELOPMENT } = require('../config/env');
const logger = require('../utils/logger');

exports.signup = async (req, res, next) => {
  try {
    const { username, email, password } = req.body;

    // Check for duplicate email
    const existingUser = await User.findByEmail(email);
    if (existingUser) {
      return res.status(409).json({
        success: false,
        message: 'An account with this email already exists'
      });
    }

    // Check for duplicate username
    const existingUsername = await User.findByUsername(username);
    if (existingUsername) {
      return res.status(409).json({
        success: false,
        message: 'This username is already taken'
      });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, SALT_ROUNDS);

    // Create new user
    const newUser = await User.create({
      username: username.trim(),
      email: email.toLowerCase().trim(),
      password: hashedPassword
    });

    if (IS_DEVELOPMENT) {
      logger.info(`New user registered: ${username} (${email})`);
    }

    // Return success response (without password)
    const userResponse = newUser.toJSON();
    delete userResponse.password;
    
    res.status(201).json({
      success: true,
      message: 'Account created successfully',
      user: userResponse
    });
  } catch (error) {
    next(error);
  }
};

exports.login = async (req, res, next) => {
  try {
    const { email, password } = req.body;

    // Find user by email
    const user = await User.findByEmail(email);
    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password'
      });
    }

    // Verify password
    const isValidPassword = await bcrypt.compare(password, user.password);
    if (!isValidPassword) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password'
      });
    }

    // Update last login time
    await user.update({ lastLogin: new Date() });

    if (IS_DEVELOPMENT) {
      logger.info(`User logged in: ${user.username} (${user.email})`);
    }

    // Create session token
    const token = createSession(user);

    // Return success response (without password)
    const userResponse = user.toJSON();
    delete userResponse.password;

    res.status(200).json({
      success: true,
      message: 'Login successful',
      user: userResponse,
      token: token
    });
  } catch (error) {
    next(error);
  }
};

exports.logout = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (token) {
      deleteSession(token);
      if (IS_DEVELOPMENT) {
        logger.info('User logged out');
      }
    }
    
    res.status(200).json({
      success: true,
      message: 'Logged out successfully'
    });
  } catch (error) {
    next(error);
  }
};

exports.getMe = async (req, res, next) => {
  try {
    const user = await User.findByPk(req.user.userId);
    
    if (!user) {
      return res.status(404).json({
        success: false,
        message: 'User not found'
      });
    }
    
    const userResponse = user.toJSON();
    delete userResponse.password;

    res.status(200).json({
      success: true,
      user: userResponse
    });
  } catch (error) {
    next(error);
  }
};

exports.verifySession = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '') || req.body.token;
    const session = getSession(token);
    
    if (session) {
      res.status(200).json({
        success: true,
        valid: true,
        user: session
      });
    } else {
      res.status(401).json({
        success: false,
        valid: false,
        message: 'Invalid or expired session'
      });
    }
  } catch (error) {
    next(error);
  }
};

exports.googleLogin = async (req, res, next) => {
  try {
    const { token, user: googleUser } = req.body;

    if (!token || !googleUser) {
      return res.status(400).json({
        success: false,
        message: 'Missing Google token or user data'
      });
    }

    // Check if user exists by Google ID or Email
    let user = await User.findByGoogleId(googleUser.sub) || await User.findByEmail(googleUser.email);

    if (!user) {
      // Create new user from Google data
      user = await User.create({
        googleId: googleUser.sub,
        username: googleUser.name || googleUser.email.split('@')[0],
        email: googleUser.email.toLowerCase(),
        avatar: googleUser.picture,
        lastLogin: new Date()
      });
      
      if (IS_DEVELOPMENT) {
        logger.info(`New Google user registered: ${user.email}`);
      }
    } else {
      // Update existing user with Google ID if missing
      const updates = { lastLogin: new Date() };
      if (!user.googleId) updates.googleId = googleUser.sub;
      if (!user.avatar) updates.avatar = googleUser.picture;
      
      await user.update(updates);

      if (IS_DEVELOPMENT) {
        logger.info(`Google user logged in: ${user.email}`);
      }
    }

    // Create session
    const sessionToken = createSession(user);

    const userResponse = user.toJSON();
    delete userResponse.password;

    res.status(200).json({
      success: true,
      message: 'Google login successful',
      user: userResponse,
      token: sessionToken
    });

  } catch (error) {
    next(error);
  }
};
