import React, { useState } from 'react';
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, Dumbbell, Database, Activity as Muscle, LogOut, BarChart3, Menu, X } from 'lucide-react';
import { getCurrentUser, clearToken, getUserRole } from '@/utils/auth';

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const user = getCurrentUser();
    const role = getUserRole();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const handleLogout = () => {
        clearToken();
        navigate('/login');
    };

    // Close sidebar when route changes on mobile
    React.useEffect(() => {
        setIsSidebarOpen(false);
    }, [location.pathname]);

    return (
        <div className="flex h-screen bg-gray-100">
            {/* Mobile Header */}
            <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white shadow-sm z-30 flex items-center px-4 justify-between">
                <div className="flex items-center">
                    <button
                        onClick={() => setIsSidebarOpen(true)}
                        className="p-2 -ml-2 rounded-md text-gray-700 hover:bg-gray-100 focus:outline-none"
                    >
                        <Menu className="w-6 h-6" />
                    </button>
                    <span className="ml-3 font-bold text-lg text-gray-800">Gym Bot</span>
                </div>
            </div>

            {/* Overlay */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`
                fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-md flex flex-col transition-transform duration-300 ease-in-out
                md:relative md:translate-x-0
                ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
            `}>
                <div className="p-6 flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-800">Gym Bot {role === 'admin' ? 'Admin' : 'Portal'}</h1>
                        {user && (
                            <div className="mt-2 text-sm text-gray-600">
                                <p className="font-medium">{user.firstName} {user.lastName}</p>
                                {user.username && <p className="text-xs">@{user.username}</p>}
                                <p className="text-xs mt-1 text-blue-600 capitalize">{role}</p>
                            </div>
                        )}
                    </div>
                    {/* Close button for mobile */}
                    <button
                        onClick={() => setIsSidebarOpen(false)}
                        className="md:hidden p-1 text-gray-500 hover:bg-gray-100 rounded-full"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <nav className="mt-6 flex-1 px-2 space-y-1">
                    {role === 'admin' && (
                        <>
                            <Link to="/" className="flex items-center px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
                                <LayoutDashboard className="w-5 h-5 mr-3" />
                                Dashboard
                            </Link>
                            <Link to="/exercises" className="flex items-center px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
                                <Dumbbell className="w-5 h-5 mr-3" />
                                Exercises
                            </Link>
                            <Link to="/muscles" className="flex items-center px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
                                <Muscle className="w-5 h-5 mr-3" />
                                Muscles
                            </Link>
                            <Link to="/training" className="flex items-center px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
                                <Database className="w-5 h-5 mr-3" />
                                All Training Data
                            </Link>
                        </>
                    )}
                    {role === 'user' && (
                        <>
                            <Link to="/my-training" className="flex items-center px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg">
                                <BarChart3 className="w-5 h-5 mr-3" />
                                My Training
                            </Link>
                        </>
                    )}
                </nav>
                <div className="p-4 border-t border-gray-200">
                    <button
                        onClick={handleLogout}
                        className="flex items-center w-full px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition"
                    >
                        <LogOut className="w-5 h-5 mr-3" />
                        Logout
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto p-4 md:p-8 pt-20 md:pt-8">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
