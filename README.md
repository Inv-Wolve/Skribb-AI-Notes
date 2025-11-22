# Skribb AI

Skribb AI is a note transformation platform that combines OCR capabilities, AI-powered text enhancement, and user management. The application processes handwritten or typed notes from images, extracts text using OCR, and applies AI enhancements for readability, grammar, and professionalism.

## Features
- AI-powered text enhancement with grammar and clarity improvements
- OCR processing using PaddleOCR for handwritten and typed notes
- Real-time text streaming via Server-Sent Events
- User authentication and management with secure password handling
- Multi-page responsive frontend built with Tailwind CSS
- Open source architecture designed for extensibility and community contributions

## Architecture
- **Node.js Server**: Handles authentication, image uploads, AI text enhancement, and acts as middleware between frontend and OCR server
- **Python FastAPI OCR Server**: Processes images and extracts text with PaddleOCR
- **Frontend**: Multi-page HTML application with Tailwind CSS, fully responsive, mobile-first design

## Setup

### Prerequisites
- Node.js
- Python 3.x
- NPM and pip installed

### Installation
1. Clone the repository
```bash
git clone <repository_url>
cd skribb-ai



- **PLEASE NOTE, SKRIBB AI IS NOT COMPLETED. IT IS IN BETA PHASE, SO NOT ALL FEATURES WILL WORK AS EXPECTED. (Feel free to open issues)**