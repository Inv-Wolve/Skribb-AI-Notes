const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');
const User = require('./User');

const Note = sequelize.define('Note', {
  id: {
    type: DataTypes.STRING,
    primaryKey: true,
    defaultValue: () => Date.now().toString()
  },
  title: {
    type: DataTypes.STRING,
    allowNull: true
  },
  content: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  type: {
    type: DataTypes.STRING,
    defaultValue: 'Document'
  },
  status: {
    type: DataTypes.STRING,
    defaultValue: 'processing'
  },
  userId: {
    type: DataTypes.STRING,
    allowNull: false,
    references: {
      model: User,
      key: 'id'
    }
  }
}, {
  timestamps: true
});

// Define relationship
User.hasMany(Note, { foreignKey: 'userId' });
Note.belongsTo(User, { foreignKey: 'userId' });

// Helper methods to match previous API
Note.findByUserId = async function(userId) {
  return await this.findAll({ where: { userId: userId } });
};

module.exports = Note;
