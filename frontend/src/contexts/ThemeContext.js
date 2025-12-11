import React, { createContext, useContext } from 'react';

// Dark mode removed per recent UI direction. ThemeProvider is now a light-mode no-op.
const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const theme = 'light';
  const toggle = () => {
    // no-op: dark mode disabled
    return;
  };

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

export default ThemeContext;
