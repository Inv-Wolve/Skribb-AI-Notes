const Note = require('../models/Note');
const logger = require('../utils/logger');

exports.getNotes = async (req, res) => {
  try {
    const notes = await Note.findAll({
      where: { userId: req.user.id },
      order: [['createdAt', 'DESC']]
    });
    res.json({ success: true, notes });
  } catch (error) {
    logger.error('Get notes error:', error);
    res.status(500).json({ success: false, message: 'Failed to fetch notes' });
  }
};

exports.createNote = async (req, res) => {
  try {
    const { title, content, type, status } = req.body;
    
    // Allow empty title for uploads, but default if missing
    const noteTitle = title || 'Untitled Note';

    const note = await Note.create({
      userId: req.user.id,
      title: noteTitle,
      content: content || '',
      type: type || 'Document',
      status: status || 'processing'
    });

    res.status(201).json({ success: true, note });
  } catch (error) {
    logger.error('Create note error:', error);
    res.status(500).json({ success: false, message: 'Failed to create note' });
  }
};

exports.updateNote = async (req, res) => {
  try {
    const { id } = req.params;
    const updates = req.body;
    
    // Prevent updating ownership or id
    delete updates.userId;
    delete updates.id;

    const note = await Note.findByPk(id);
    if (!note) {
      return res.status(404).json({ success: false, message: 'Note not found' });
    }

    if (note.userId !== req.user.id) {
      return res.status(403).json({ success: false, message: 'Not authorized' });
    }

    await note.update(updates);
    res.json({ success: true, note });
  } catch (error) {
    logger.error('Update note error:', error);
    res.status(500).json({ success: false, message: 'Failed to update note' });
  }
};

exports.deleteNote = async (req, res) => {
  try {
    const { id } = req.params;
    
    const note = await Note.findByPk(id);
    if (!note) {
      return res.status(404).json({ success: false, message: 'Note not found' });
    }

    if (note.userId !== req.user.id) {
      return res.status(403).json({ success: false, message: 'Not authorized' });
    }

    await note.destroy();
    res.json({ success: true, message: 'Note deleted successfully' });
  } catch (error) {
    logger.error('Delete note error:', error);
    res.status(500).json({ success: false, message: 'Failed to delete note' });
  }
};
