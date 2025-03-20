// src/App.tsx

import React from 'react';
import ChatBot from './chatScreen/ChatBot';
import './App.css'; // Import the CSS file

function App() {
  return (
    <div className="App">
      <h1>Timesheet Demo Application</h1>
      <ChatBot />
    </div>
  );
}

export default App;