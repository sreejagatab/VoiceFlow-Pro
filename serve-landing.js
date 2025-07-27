const express = require('express');
const path = require('path');
const app = express();
const PORT = 8080;

// Serve static files from root directory
app.use(express.static('.'));

// Route for root - serve landing page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'landing-page.html'));
});

// Route for app - proxy to frontend
app.get('/app', (req, res) => {
  res.redirect('http://localhost:3000');
});

// Route for demo video
app.get('/demo-video', (req, res) => {
  res.sendFile(path.join(__dirname, 'VoiceFlow Pro - Business Automation Voice Agent - Google Chrome 2025-07-27 16-23-50.mp4'));
});

// Serve other static files
app.get('*', (req, res) => {
  const filePath = path.join(__dirname, req.path);
  res.sendFile(filePath, (err) => {
    if (err) {
      res.status(404).send('File not found');
    }
  });
});

app.listen(PORT, () => {
  console.log(`🌟 Landing page server running at http://localhost:${PORT}`);
  console.log(`📱 Frontend app available at http://localhost:3000`);
  console.log(`🎬 Demo video at http://localhost:${PORT}/demo-video`);
});
