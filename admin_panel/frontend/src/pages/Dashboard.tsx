import React from 'react';

const Dashboard = () => {
    return (
        <div>
            <h2 className="text-3xl font-bold text-gray-800 mb-6">Dashboard</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-xl font-semibold text-gray-700 mb-2">Welcome</h3>
                    <p className="text-gray-600">Welcome to the Gym Bot Admin Panel.</p>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
