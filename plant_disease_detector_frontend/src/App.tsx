import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import { PlantDataProvider } from './contexts/PlantDataContext';
import Login from './components/auth/Login';
import Signup from './components/auth/Signup';
import Dashboard from './components/dashboard/Dashboard';
import ProtectedRoute from './components/auth/ProtectedRoute';
import './i18n';
import { AppProvider } from './contexts/AppContext';

function App() {

  return (
    <AuthProvider>
      <AppProvider>
      <PlantDataProvider>
        <Router>
          <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route 
                path="/dashboard" 
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                } 
              />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
            <Toaster 
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#10B981',
                  color: '#fff',
                },
              }}
            />
          </div>
        </Router>
      </PlantDataProvider>
      </AppProvider>
    </AuthProvider>
  );
}

export default App;