import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Plus, Edit2 } from 'lucide-react';
import TrainingModal from '@/components/TrainingModal';

interface User {
    id: number;
    first_name?: string;
    lastname?: string;
    username?: string;
}

interface Exercise {
    id: number;
    name: string;
    muscle_id?: number; // Added for edit context
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
    exercise?: Exercise;
}

const MyTraining = () => {
    const [trainingData, setTrainingData] = useState<Training[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingTraining, setEditingTraining] = useState<Training | undefined>(undefined);

    useEffect(() => {
        fetchTrainingData();
    }, []);

    const fetchTrainingData = async () => {
        try {
            setLoading(true);
            const response = await api.get('/user/training');
            setTrainingData(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load training data');
        } finally {
            setLoading(false);
        }
    };

    const handleAddClick = () => {
        setEditingTraining(undefined);
        setIsModalOpen(true);
    };

    const handleEditClick = (training: Training) => {
        setEditingTraining(training);
        setIsModalOpen(true);
    };

    const handleSave = () => {
        fetchTrainingData(); // Refresh data after save
    };

    if (loading && trainingData.length === 0) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                {error}
            </div>
        );
    }

    return (
        <div className="relative min-h-screen pb-20"> {/* Added padding for FAB */}
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-3xl font-bold text-gray-800">My Training</h2>
                <button
                    onClick={handleAddClick}
                    className="hidden md:flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <Plus size={20} className="mr-2" />
                    Add Training
                </button>
            </div>

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="overflow-x-auto"> {/* Added for horizontal scroll on small screens */}
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Exercise</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Set</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reps</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {trainingData.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                                        No training data yet. Start working out!
                                    </td>
                                </tr>
                            ) : (
                                trainingData.map((record) => (
                                    <tr key={record.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {new Date(record.date).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                                            {record.exercise?.name || `ID: ${record.exercise_id}`}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.set}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.weight}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{record.reps}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <button
                                                onClick={() => handleEditClick(record)}
                                                className="text-blue-600 hover:text-blue-900 p-2 rounded-full hover:bg-blue-50 transition-colors"
                                            >
                                                <Edit2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Mobile Floating Action Button */}
            <button
                onClick={handleAddClick}
                className="md:hidden fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-colors z-40"
            >
                <Plus size={24} />
            </button>

            <TrainingModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSave={handleSave}
                editData={editingTraining}
            />
        </div>
    );
};

export default MyTraining;
