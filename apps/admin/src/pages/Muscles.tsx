import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

interface Muscle {
    id: number;
    name: string;
}

const Muscles = () => {
    const [muscles, setMuscles] = useState<Muscle[]>([]);

    // UI State
    const [isEditMode, setIsEditMode] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Form State
    const [newMuscleName, setNewMuscleName] = useState('');
    const [validationError, setValidationError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Editing State
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editName, setEditName] = useState('');

    useEffect(() => {
        fetchMuscles();
    }, []);

    const fetchMuscles = async () => {
        try {
            const response = await api.get('/muscles');
            setMuscles(response.data);
        } catch (error) {
            console.error('Error fetching muscles:', error);
        }
    };

    // Validation Logic
    useEffect(() => {
        if (!newMuscleName) {
            setValidationError(null);
            return;
        }

        const normalizedName = newMuscleName.trim().toLowerCase();
        const exists = muscles.some(m => m.name.toLowerCase() === normalizedName);

        if (exists) {
            setValidationError('This muscle group already exists.');
        } else {
            setValidationError(null);
        }
    }, [newMuscleName, muscles]);

    const handleAddMuscle = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newMuscleName || validationError) return;

        setIsSubmitting(true);
        try {
            await api.post('/muscles', {
                name: newMuscleName,
            });

            setNewMuscleName('');
            setIsModalOpen(false);
            fetchMuscles();
        } catch (error) {
            console.error('Error adding muscle:', error);
            alert('Failed to add muscle. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const openAddModal = () => {
        setNewMuscleName('');
        setValidationError(null);
        setIsModalOpen(true);
    };

    const handleEditClick = (muscle: Muscle) => {
        setEditingId(muscle.id);
        setEditName(muscle.name);
    };

    const handleCancelEdit = () => {
        setEditingId(null);
        setEditName('');
    };

    const handleSaveEdit = async () => {
        if (!editingId) return;
        try {
            await api.put(`/muscles/${editingId}`, {
                name: editName,
            });
            setEditingId(null);
            fetchMuscles();
        } catch (error) {
            console.error('Error updating muscle:', error);
            alert('Failed to update muscle. It might be a duplicate.');
        }
    };

    return (
        <div>
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <h2 className="text-3xl font-bold text-gray-800">Muscle Groups</h2>

                <div className="flex items-center gap-4">
                    {/* Edit Mode Toggle */}
                    <button
                        onClick={() => setIsEditMode(!isEditMode)}
                        className={`px-4 py-2 rounded-md transition-colors ${isEditMode
                                ? 'bg-gray-800 text-white hover:bg-gray-900'
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                    >
                        {isEditMode ? 'Exit Edit Mode' : 'Edit Mode'}
                    </button>

                    {/* Add Button (Only in Edit Mode) */}
                    {isEditMode && (
                        <button
                            onClick={openAddModal}
                            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center gap-2 shadow-sm"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Add Muscle
                        </button>
                    )}
                </div>
            </div>

            {/* Muscles List */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden border border-gray-200">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">ID</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                {isEditMode && <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-24">Actions</th>}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {muscles.length > 0 ? (
                                muscles.map((muscle) => (
                                    <tr key={muscle.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {muscle.id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                            {editingId === muscle.id ? (
                                                <input
                                                    type="text"
                                                    className="border border-gray-300 rounded px-2 py-1 w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                    value={editName}
                                                    onChange={(e) => setEditName(e.target.value)}
                                                />
                                            ) : (
                                                muscle.name
                                            )}
                                        </td>
                                        {isEditMode && (
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                {editingId === muscle.id ? (
                                                    <div className="flex justify-end gap-2">
                                                        <button
                                                            onClick={handleSaveEdit}
                                                            className="text-green-600 hover:text-green-900"
                                                            title="Save"
                                                        >
                                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                            </svg>
                                                        </button>
                                                        <button
                                                            onClick={handleCancelEdit}
                                                            className="text-red-600 hover:text-red-900"
                                                            title="Cancel"
                                                        >
                                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <button
                                                        onClick={() => handleEditClick(muscle)}
                                                        className="text-blue-600 hover:text-blue-900"
                                                        title="Edit"
                                                    >
                                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                                        </svg>
                                                    </button>
                                                )}
                                            </td>
                                        )}
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={isEditMode ? 3 : 2} className="px-6 py-12 text-center text-gray-500">
                                        No muscle groups found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 text-sm text-gray-500">
                    Showing {muscles.length} muscle groups
                </div>
            </div>

            {/* Add Muscle Modal */}
            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title="Add New Muscle Group"
            >
                <form onSubmit={handleAddMuscle} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Muscle Name
                        </label>
                        <input
                            type="text"
                            placeholder="e.g. Chest"
                            className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 ${validationError
                                    ? 'border-red-500 focus:ring-red-500 bg-red-50'
                                    : 'border-gray-300 focus:ring-blue-500'
                                }`}
                            value={newMuscleName}
                            onChange={(e) => setNewMuscleName(e.target.value)}
                            required
                        />
                        {validationError && (
                            <p className="mt-1 text-sm text-red-600 font-medium animate-pulse">
                                {validationError}
                            </p>
                        )}
                    </div>

                    <div className="flex justify-end gap-3 mt-6">
                        <button
                            type="button"
                            onClick={() => setIsModalOpen(false)}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!!validationError || !newMuscleName || isSubmitting}
                            className={`px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${validationError || !newMuscleName || isSubmitting
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 hover:bg-blue-700'
                                }`}
                        >
                            {isSubmitting ? 'Saving...' : 'Save Muscle'}
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
};

export default Muscles;
