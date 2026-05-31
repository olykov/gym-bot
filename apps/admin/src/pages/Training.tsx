import React, { useEffect, useState } from 'react';
import api from '@/lib/api';

interface User {
    id: number;
    first_name?: string;
    lastname?: string;
    username?: string;
}

interface Training {
    id: string;
    date: string;
    user_id: number;
    muscle_id: number;
    exercise_id: number;
    set: number;
    weight: number;
    reps: number;
    user?: User;
}

const Training = () => {
    const [trainingData, setTrainingData] = useState<Training[]>([]);

    useEffect(() => {
        fetchTrainingData();
    }, []);

    const fetchTrainingData = async () => {
        try {
            const response = await api.get('/training');
            setTrainingData(response.data);
        } catch (error) {
            console.error('Error fetching training data:', error);
        }
    };

    const getUserDisplay = (record: Training): string => {
        if (!record.user) {
            return String(record.user_id);
        }

        const { first_name, lastname, username, id } = record.user;

        // Priority: "first_name lastname" > "username" > "id"
        if (first_name || lastname) {
            return `${first_name || ''} ${lastname || ''}`.trim();
        }

        if (username) {
            return username;
        }

        return String(id);
    };

    return (
        <div>
            <h2 className="text-3xl font-bold text-gray-800 mb-6">Training Data</h2>
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Exercise ID</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Set</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reps</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {trainingData.map((record) => (
                            <tr key={record.id}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {new Date(record.date).toLocaleDateString()}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                                    {getUserDisplay(record)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.exercise_id}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.set}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.weight}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.reps}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Training;
