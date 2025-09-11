import React, { useState } from 'react';
import Link from 'next/link';
import UserProfile from './auth/UserProfile';
import BurgerMenu from './BurgerMenu';

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

const Header: React.FC<HeaderProps> = ({ 
  title = "Gym Progress Analytics",
  subtitle = "Personal Fitness Dashboard"
}) => {
  const [isBurgerMenuOpen, setIsBurgerMenuOpen] = useState(false);

  const toggleBurgerMenu = () => {
    setIsBurgerMenuOpen(!isBurgerMenuOpen);
  };

  return (
    <>
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {/* Burger Menu Button */}
              <button
                onClick={toggleBurgerMenu}
                className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-full hover:bg-blue-700 transition-colors"
                aria-label="Open navigation menu"
              >
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              
              <div>
                <Link href="/profile" className="text-xl font-bold text-gray-900 hover:text-gray-700">
                  {title}
                </Link>
                <p className="text-sm text-gray-600">{subtitle}</p>
              </div>
            </div>
            
            <UserProfile />
          </div>
        </div>
      </header>

      {/* Burger Menu Component */}
      <BurgerMenu isOpen={isBurgerMenuOpen} onToggle={toggleBurgerMenu} />
    </>
  );
};

export default Header;