import * as React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import App from './App';
import { createTheme } from '@mui/material/styles';
import { red } from '@mui/material/colors';
import { useState, useEffect } from 'react';

function RootApp() {
  const [mode, setMode] = useState('light');

useEffect(() => {
    setMode(window.localStorage.getItem('theme') || 'light');
}, []);

var observer = new MutationObserver(function(mutations) {
  setMode(window.localStorage.getItem('theme') || 'light');
  
})
observer.observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

// A custom theme for this app
const theme = createTheme({
  palette: {
    mode: mode == 'light' ? 'light' : 'dark',
  },
  cssVariables: true
});

  return (
    <ThemeProvider theme={theme}>
    <CssBaseline />
    <App  />
  </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>,
);

