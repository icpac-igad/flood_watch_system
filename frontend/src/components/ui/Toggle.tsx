/**
 * Toggle Switch Component - Pure Tailwind CSS
 * Replaces toggle-switch-small and toggle-slider-small CSS classes
 */

import React from 'react';

interface ToggleProps {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}

export const Toggle: React.FC<ToggleProps> = ({ 
  id, 
  checked, 
  onChange, 
  label,
  disabled = false 
}) => {
  return (
    <div className="flex items-center gap-2">
      <div className="relative inline-block w-[30px] h-4">
        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="opacity-0 w-0 h-0 peer"
        />
        <label
          htmlFor={id}
          className={`
            absolute cursor-pointer top-0 left-0 right-0 bottom-0
            bg-gray-300 rounded-2xl transition-all duration-400
            before:absolute before:content-[''] before:h-2.5 before:w-2.5
            before:left-0.5 before:bottom-[3px] before:bg-white
            before:rounded-full before:transition-all before:duration-400
            peer-checked:bg-blue-500
            peer-checked:before:translate-x-[14px]
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        />
      </div>
      {label && (
        <label htmlFor={id} className="text-sm cursor-pointer">
          {label}
        </label>
      )}
    </div>
  );
};
