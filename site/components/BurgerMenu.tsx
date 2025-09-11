import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

interface BurgerMenuProps {
  isOpen: boolean;
  onToggle: () => void;
}

const BurgerMenu: React.FC<BurgerMenuProps> = ({ isOpen, onToggle }) => {
  const router = useRouter();

  const menuItems = [
    { href: '/profile', label: 'Profile', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
    { href: '/exercises', label: 'Exercises', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
    { href: '/exercises/chest/bench%20press', label: 'Statistics', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { href: '/sets-distribution', label: 'Sets Distribution', icon: 'M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z' },
    { href: '#', label: 'Edit Trainings', icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z' }
  ];

  const isActive = (href: string) => {
    if (href === '#') return false;
    return router.pathname === href;
  };

  const handleItemClick = () => {
    onToggle(); // Close menu when item is clicked
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity duration-300"
          onClick={onToggle}
        />
      )}
      
      {/* Slide-out Menu */}
      <div className={`fixed top-0 right-0 h-full w-80 bg-white shadow-lg z-50 transform transition-transform duration-300 ease-in-out ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Menu Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold text-gray-900">Navigation</h2>
          <button
            onClick={onToggle}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Menu Items */}
        <nav className="p-6">
          <ul className="space-y-4">
            {menuItems.map((item, index) => (
              <li key={index}>
                {item.href === '#' ? (
                  <button
                    onClick={handleItemClick}
                    className="flex items-center w-full p-3 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                    </svg>
                    {item.label}
                  </button>
                ) : (
                  <Link
                    href={item.href}
                    onClick={handleItemClick}
                    className={`flex items-center p-3 rounded-lg transition-colors ${
                      isActive(item.href)
                        ? 'bg-blue-50 text-blue-600 font-medium'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                    </svg>
                    {item.label}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </nav>

        {/* Menu Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-6 border-t bg-gray-50">
          <div className="text-center text-sm text-gray-500">
            <p>🏋️ Gym Progress Analytics</p>
            <p className="mt-1">Track your fitness journey</p>
          </div>
        </div>
      </div>
    </>
  );
};

export default BurgerMenu;