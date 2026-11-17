import React from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'
document.documentElement.dataset.theme = localStorage.getItem('theme') || 'light'
createRoot(document.getElementById('root')).render(<HashRouter><App /></HashRouter>)
