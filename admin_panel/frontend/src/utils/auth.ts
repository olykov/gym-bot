// Auth utility functions for managing JWT tokens

const TOKEN_KEY = 'admin_auth_token';

export const getToken = (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = (): void => {
    localStorage.removeItem(TOKEN_KEY);
};

export const isAuthenticated = (): boolean => {
    const token = getToken();
    if (!token) return false;

    try {
        // Decode JWT to check expiration
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000; // Convert to milliseconds
        return Date.now() < exp;
    } catch {
        return false;
    }
};

export const getCurrentUser = (): any | null => {
    const token = getToken();
    if (!token) return null;

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return {
            id: payload.sub,
            firstName: payload.first_name,
            lastName: payload.last_name,
            username: payload.username,
            photoUrl: payload.photo_url,
            authType: payload.auth_type,
            role: payload.role  // Extract role from JWT
        };
    } catch {
        return null;
    }
};

export const getUserRole = (): 'admin' | 'user' | null => {
    const user = getCurrentUser();
    return user?.role || null;
};

export const isAdmin = (): boolean => {
    return getUserRole() === 'admin';
};
