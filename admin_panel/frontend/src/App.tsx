import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/ui/Layout';
import Dashboard from '@/pages/Dashboard';
import Exercises from '@/pages/Exercises';
import Muscles from '@/pages/Muscles';
import Training from '@/pages/Training';
import MyTraining from '@/pages/MyTraining';
import Login from '@/pages/Login';
import { isAuthenticated, getUserRole } from '@/utils/auth';

// Protected Route wrapper
const ProtectedRoute = ({ children, requiredRole }: { children: React.ReactNode; requiredRole?: 'admin' | 'user' }) => {
    if (!isAuthenticated()) {
        return <Navigate to="/login" replace />;
    }

    // If a specific role is required, check it
    if (requiredRole) {
        const userRole = getUserRole();
        if (userRole !== requiredRole) {
            // Redirect to appropriate default page
            return <Navigate to={userRole === 'admin' ? '/' : '/my-training'} replace />;
        }
    }

    return <>{children}</>;
};

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/" element={
                    <ProtectedRoute>
                        <Layout />
                    </ProtectedRoute>
                }>
                    {/* Admin routes */}
                    <Route index element={
                        <ProtectedRoute requiredRole="admin">
                            <Dashboard />
                        </ProtectedRoute>
                    } />
                    <Route path="exercises" element={
                        <ProtectedRoute requiredRole="admin">
                            <Exercises />
                        </ProtectedRoute>
                    } />
                    <Route path="muscles" element={
                        <ProtectedRoute requiredRole="admin">
                            <Muscles />
                        </ProtectedRoute>
                    } />
                    <Route path="training" element={
                        <ProtectedRoute requiredRole="admin">
                            <Training />
                        </ProtectedRoute>
                    } />

                    {/* User routes */}
                    <Route path="my-training" element={
                        <ProtectedRoute requiredRole="user">
                            <MyTraining />
                        </ProtectedRoute>
                    } />
                </Route>
            </Routes>
        </Router>
    );
}

export default App;
