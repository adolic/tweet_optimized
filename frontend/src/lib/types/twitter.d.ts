declare global {
    interface Window {
        twq?: (command: string, event: string, params?: object) => void;
    }
}

export {}; 