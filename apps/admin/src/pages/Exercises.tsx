import React, { useEffect, useState, useMemo } from 'react';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';

interface Muscle {
    id: number;
    name: string;
}

interface Exercise {
    id: number;
    name: string;
    muscle: number;
}

const Exercises = () => {
    const [exercises, setExercises] = useState<Exercise[]>([]);
    const [muscles, setMuscles] = useState<Muscle[]>([]);

    // UI State
    const [isEditMode, setIsEditMode] = useState(false);
    const [filterMuscleId, setFilterMuscleId] = useState<string>('');
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Form State
    const [newExerciseName, setNewExerciseName] = useState('');
    const [newExerciseMuscleId, setNewExerciseMuscleId] = useState<string>('');
    const [validationError, setValidationError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Editing State
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<{ name: string; muscleId: string }>({ name: '', muscleId: '' });

    useEffect(() => {
        fetchExercises();
        fetchMuscles();
    }, []);

    const fetchExercises = async () => {
        try {
            // Fetching a larger limit to ensure we have all exercises for client-side validation
            const response = await api.get('/exercises?limit=1000');
            setExercises(response.data);
        } catch (error) {
            console.error('Error fetching exercises:', error);
        }
    };

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
        if (!newExerciseName || !newExerciseMuscleId) {
            setValidationError(null);
            return;
        }

        const muscleId = parseInt(newExerciseMuscleId);
        const normalizedName = newExerciseName.trim().toLowerCase();

        const exists = exercises.some(
            ex => ex.muscle === muscleId && ex.name.toLowerCase() === normalizedName
        );

        if (exists) {
            setValidationError('This exercise already exists for the selected muscle group.');
        } else {
            setValidationError(null);
        }
    }, [newExerciseName, newExerciseMuscleId, exercises]);

    const handleAddExercise = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newExerciseName || !newExerciseMuscleId || validationError) return;

        setIsSubmitting(true);
        try {
            await api.post('/exercises', {
                name: newExerciseName,
                muscle: parseInt(newExerciseMuscleId),
            });

            // Reset form and close modal
            setNewExerciseName('');
            // Keep the muscle selected for convenience if adding multiple
            // setNewExerciseMuscleId(''); 
            setIsModalOpen(false);

            // Refresh list
            fetchExercises();
        } catch (error) {
            console.error('Error adding exercise:', error);
            alert('Failed to add exercise. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const openAddModal = () => {
        // Pre-select the filter muscle if one is active
        if (filterMuscleId) {
            setNewExerciseMuscleId(filterMuscleId);
        }
        setNewExerciseName('');
        setValidationError(null);
        setIsModalOpen(true);
    };

    const handleEditClick = (exercise: Exercise) => {
        setEditingId(exercise.id);
        setEditForm({ name: exercise.name, muscleId: exercise.muscle.toString() });
    };

    const handleCancelEdit = () => {
        setEditingId(null);
        setEditForm({ name: '', muscleId: '' });
    };

    const handleSaveEdit = async () => {
        if (!editingId) return;
        try {
            await api.put(`/exercises/${editingId}`, {
                name: editForm.name,
                muscle: parseInt(editForm.muscleId)
            });
            setEditingId(null);
            fetchExercises();
        } catch (error) {
            console.error('Error updating exercise:', error);
            alert('Failed to update exercise. It might be a duplicate.');
        }
    };

    // Filtered Exercises
    const filteredExercises = useMemo(() => {
        if (!filterMuscleId) return exercises;
        const id = parseInt(filterMuscleId);
        return exercises.filter(ex => ex.muscle === id);
    }, [exercises, filterMuscleId]);

    // Helper to get muscle name
    const getMuscleName = (id: number) => {
        return muscles.find(m => m.id === id)?.name || id;
    };

    return (
        <div>
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <h2 className="text-3xl font-bold text-gray-800">Exercises</h2>

                <div className="flex items-center gap-4">
                    {/* Muscle Filter */}
                    <select
                        className="border border-gray-300 rounded-md px-4 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={filterMuscleId}
                        onChange={(e) => setFilterMuscleId(e.target.value)}
                    >
                        <option value="">All Muscle Groups</option>
                        {muscles.map((muscle) => (
                            <option key={muscle.id} value={muscle.id}>
                                {muscle.name}
                            </option>
                        ))}
                    </select>

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
                            Add Exercise
                        </button>
                    )}
                </div>
            </div>

            {/* Exercises List */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden border border-gray-200">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">ID</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Muscle Group</th>
                                {isEditMode && <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-24">Actions</th>}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredExercises.length > 0 ? (
                                filteredExercises.map((exercise) => (
                                    <tr key={exercise.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {exercise.id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                            {editingId === exercise.id ? (
                                                <input
                                                    type="text"
                                                    className="border border-gray-300 rounded px-2 py-1 w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                    value={editForm.name}
                                                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                                />
                                            ) : (
                                                exercise.name
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {editingId === exercise.id ? (
                                                <select
                                                    className="border border-gray-300 rounded px-2 py-1 w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                    value={editForm.muscleId}
                                                    onChange={(e) => setEditForm({ ...editForm, muscleId: e.target.value })}
                                                >
                                                    {muscles.map((m) => (
                                                        <option key={m.id} value={m.id}>{m.name}</option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                    {getMuscleName(exercise.muscle)}
                                                </span>
                                            )}
                                        </td>
                                        {isEditMode && (
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                {editingId === exercise.id ? (
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
                                                        onClick={() => handleEditClick(exercise)}
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
                                    <td colSpan={3} className="px-6 py-12 text-center text-gray-500">
                                        No exercises found. Try changing the filter.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 text-sm text-gray-500">
                    Showing {filteredExercises.length} exercises
                </div>
            </div>

            {/* Add Exercise Modal */}
            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title="Add New Exercise"
            >
                <form onSubmit={handleAddExercise} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Muscle Group
                        </label>
                        <select
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={newExerciseMuscleId}
                            onChange={(e) => setNewExerciseMuscleId(e.target.value)}
                            required
                        >
                            <option value="">Select Muscle Group</option>
                            {muscles.map((muscle) => (
                                <option key={muscle.id} value={muscle.id}>
                                    {muscle.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Exercise Name
                        </label>
                        <input
                            type="text"
                            placeholder="e.g. Bench Press"
                            className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 ${validationError
                                ? 'border-red-500 focus:ring-red-500 bg-red-50'
                                : 'border-gray-300 focus:ring-blue-500'
                                }`}
                            value={newExerciseName}
                            onChange={(e) => setNewExerciseName(e.target.value)}
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
                            disabled={!!validationError || !newExerciseName || !newExerciseMuscleId || isSubmitting}
                            className={`px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${validationError || !newExerciseName || !newExerciseMuscleId || isSubmitting
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-blue-600 hover:bg-blue-700'
                                }`}
                        >
                            {isSubmitting ? 'Saving...' : 'Save Exercise'}
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
};

export default Exercises;
